import json
import logging
import os
import re
from typing import Dict, Optional
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class StationTranslationService:
    # 定义支持的语言代码
    available_languages = {"en", "zh", "ar", "ja", "ko", "ru", "th"}

    def __init__(self):
        self.translations: Dict[str, Dict] = {
            "train": self._load_translations("train_stations.json"),
            "metro": self._load_translations("metro_stations.json"),
            "ferry": self._load_translations("ferry_stations.json"),
            "lightrail": self._load_translations("lightrail_stations.json"),
            "trainlink": self._load_translations("trainlink_stations.json")
        }
        # 加载通用翻译
        self.common_translations = self._load_translations("common_translation.json")
        
        # 合并所有翻译以便跨模式查找
        self.all_translations = {}
        for mode_translations in self.translations.values():
            self.all_translations.update(mode_translations)
        
        # Redis缓存前缀
        self.cache_prefix = "station_translation:"
        # 缓存过期时间（24小时）
        self.cache_ttl = 86400
        
        logger.info("Station translation service initialized")
        logger.debug(f"Loaded translations for modes: {list(self.translations.keys())}")
        logger.debug(f"Total unique stations: {len(self.all_translations)}")
        logger.debug(f"Available languages: {self.available_languages}")

    async def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """从Redis缓存获取翻译结果"""
        try:
            redis = await RedisService.get_redis()
            if redis:
                cached_value = await redis.get(f"{self.cache_prefix}{cache_key}")
                if cached_value:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_value
        except Exception as e:
            logger.error(f"Error getting from Redis cache: {str(e)}")
        return None

    async def _set_to_cache(self, cache_key: str, value: str) -> None:
        """将翻译结果存入Redis缓存"""
        try:
            redis = await RedisService.get_redis()
            if redis:
                await redis.set(
                    f"{self.cache_prefix}{cache_key}",
                    value,
                    ex=self.cache_ttl
                )
                logger.debug(f"Cached translation for key: {cache_key}")
        except Exception as e:
            logger.error(f"Error setting to Redis cache: {str(e)}")

    async def translate_station_names_batch(self, 
                                          stations: list[tuple[str, str]], 
                                          language_code: str = "en") -> Dict[str, str]:
        """
        批量翻译站台名称，使用Redis缓存优化性能
        
        Args:
            stations: 包含(station_name, transport_mode)元组的列表
            language_code: 目标语言代码 (默认: "en")
            
        Returns:
            Dict[str, str]: 站台名称到翻译的映射
        """
        if not stations or language_code == "en":
            logger.debug(f"No translation needed for {len(stations) if stations else 0} stations")
            return {station[0]: station[0] for station in stations}

        # 验证language_code是否支持
        if language_code not in self.available_languages:
            logger.warning(f"Unsupported language code: {language_code}, falling back to 'en'")
            return {station[0]: station[0] for station in stations}

        logger.info(f"Starting batch translation for {len(stations)} stations to {language_code}")
        translations = {}
        # 批量获取缓存键
        cache_keys = [
            f"{station_name}_{transport_mode}_{language_code}"
            for station_name, transport_mode in stations
        ]
        
        try:
            # 批量从Redis获取缓存
            redis = await RedisService.get_redis()
            if redis:
                logger.debug(f"Fetching translations from Redis for {len(cache_keys)} keys")
                cached_results = await redis.mget([f"{self.cache_prefix}{key}" for key in cache_keys])
                
                # 处理缓存结果
                cache_hits = 0
                for i, (station_name, transport_mode) in enumerate(stations):
                    if cached_results[i]:
                        translations[station_name] = cached_results[i]
                        cache_hits += 1
                        logger.debug(f"Cache hit for '{cache_keys[i]}'")
                        continue
                        
                    # 如果缓存未命中，执行翻译
                    transport_type = self._get_transport_mode(transport_mode)
                    if not transport_type:
                        logger.warning(f"Unsupported transport mode: {transport_mode} for station {station_name}")
                        translations[station_name] = station_name
                        continue

                    result = self._translate_station_name(station_name, transport_type, language_code)
                    translations[station_name] = result
                    logger.debug(f"Translated '{station_name}' to '{result}' using {transport_type}")
                    
                    # 异步存入缓存
                    await self._set_to_cache(cache_keys[i], result)
                
                logger.info(f"Translation completed: {cache_hits} cache hits, {len(stations) - cache_hits} new translations")
        except Exception as e:
            logger.error(f"Error in batch translation with Redis: {str(e)}")
            # 发生错误时回退到非缓存模式
            for station_name, transport_mode in stations:
                transport_type = self._get_transport_mode(transport_mode)
                if not transport_type:
                    translations[station_name] = station_name
                    continue
                    
                result = self._translate_station_name(station_name, transport_type, language_code)
                translations[station_name] = result

        return translations

    def _load_translations(self, filename: str) -> Dict:
        """加载翻译文件"""
        try:
            # 根据文件名选择不同的目录
            if filename == "common_translation.json":
                file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       "data", filename)
            else:
                file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       "data", "stations", filename)
                                       
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                logger.debug(f"Successfully loaded {len(translations)} translations from {filename}")
                return translations
        except Exception as e:
            logger.error(f"Error loading translation file {filename}: {str(e)}")
            return {}

    def _get_transport_mode(self, mode_name: str) -> Optional[str]:
        """获取标准化的交通工具类型"""
        mode_name = mode_name.lower()
        logger.debug(f"Getting transport mode for: {mode_name}")
        
        if "train" in mode_name or mode_name == "t":
            return "train"
        elif "metro" in mode_name or mode_name == "m":
            return "metro"
        elif "ferry" in mode_name or mode_name == "f":
            return "ferry"
        elif "light rail" in mode_name or mode_name == "l":
            return "lightrail"
        elif "trainlink" in mode_name:
            return "trainlink"
        elif "footpath" in mode_name:
            return "footpath"
        else:
            logger.warning(f"Unknown transport mode: {mode_name}")
            return None

    def _clean_station_name(self, name: str) -> str:
        """清理站名，移除常见后缀和不必要的信息"""
        # 移除平台号
        cleaned_name = re.sub(r', Platform \d+', '', name)
        
        # 移除常见后缀
        suffixes = [
            " Station",
            " LR",  # Light Rail
            ", Sydney",
            ", Artarmon",
            ", Chatswood",
            " Platform",
            " platform",
            " Side A",
            " Side B",
            " Wharf",  # 轮渡码头
        ]
        
        # 移除其他后缀
        for suffix in suffixes:
            cleaned_name = cleaned_name.replace(suffix, "")
            
        # 移除括号内的内容
        cleaned_name = re.sub(r'\s*\([^)]*\)', '', cleaned_name)
        
        logger.debug(f"Cleaned station name: {name} -> {cleaned_name}")
        return cleaned_name.strip()

    def _translate_station_name(self, 
                              station_name: str, 
                              transport_type: str,
                              language_code: str) -> str:
        """翻译站台名称"""
        logger.debug(f"Translating station: {station_name} ({transport_type}) to {language_code}")
        
        # 如果是英文或不支持的语言，直接返回原名
        if language_code == "en" or language_code not in self.available_languages:
            return station_name
            
        # 清理站台名称
        cleaned_name = self._clean_station_name(station_name)
        logger.debug(f"Cleaned station name: {cleaned_name}")
        
        # 尝试从翻译文件中获取翻译
        if transport_type in self.translations and cleaned_name in self.translations[transport_type]:
            translation = self.translations[transport_type][cleaned_name].get(language_code)
            if translation:
                logger.debug(f"Found translation in {transport_type} translations: {translation}")
                return translation
                
        # 尝试从所有翻译中查找
        if cleaned_name in self.all_translations:
            translation = self.all_translations[cleaned_name].get(language_code)
            if translation:
                logger.debug(f"Found translation in all translations: {translation}")
                return translation
                
        # 如果没有找到翻译，返回原名
        logger.warning(f"No translation found for: {station_name}")
        return station_name 
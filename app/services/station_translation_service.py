import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StationTranslationService:
    # 定义支持的语言代码
    available_languages = {"en", "zh"}

    def __init__(self):
        self.translations: Dict[str, Dict] = {
            "train": self._load_translations("train_stations.json"),
            "metro": self._load_translations("metro_stations.json"),
            "ferry": self._load_translations("ferry_stations.json"),
            "lightrail": self._load_translations("lightrail_stations.json"),
            "trainlink": self._load_translations("trainlink_stations.json")
        }
        # 合并所有翻译以便跨模式查找
        self.all_translations = {}
        for mode_translations in self.translations.values():
            self.all_translations.update(mode_translations)
        
        logger.info("Station translation service initialized")
        logger.debug(f"Loaded translations for modes: {list(self.translations.keys())}")
        logger.debug(f"Total unique stations: {len(self.all_translations)}")
        logger.debug(f"Available languages: {self.available_languages}")

    def _load_translations(self, filename: str) -> Dict:
        """加载翻译文件"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "data", "stations", filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                logger.debug(f"Successfully loaded {len(translations)} translations from {filename}")
                return translations
        except Exception as e:
            logger.error(f"Error loading translation file {filename}: {str(e)}")
            return {}

    def _get_transport_mode(self, mode: str) -> Optional[str]:
        """根据交通工具名称返回对应的翻译文件类型"""
        if not mode:
            logger.warning("Transport mode is empty")
            return None
            
        mode_lower = mode.lower()
        logger.debug(f"Looking up transport mode mapping for: '{mode_lower}'")
        
        # 使用关键词匹配来判断交通工具类型
        if "metro" in mode_lower:  # metro是特例，不使用复数形式
            transport_mode = "metro"
        elif "trains" in mode_lower or "train" in mode_lower:
            transport_mode = "train"
        elif "ferries" in mode_lower or "ferry" in mode_lower:
            transport_mode = "ferry"
        elif "light rail" in mode_lower or "lightrail" in mode_lower:
            transport_mode = "lightrail"
        elif "trainlink" in mode_lower:
            transport_mode = "trainlink"
        else:
            transport_mode = None
            logger.warning(f"Unknown transport mode: '{mode}', available modes: train, metro, ferry, lightrail, trainlink")
            
        if transport_mode:
            logger.info(f"Successfully mapped transport mode '{mode}' to '{transport_mode}'")
            
        return transport_mode

    def _clean_station_name(self, name: str) -> str:
        """清理站名，移除常见的后缀和前缀"""
        replacements = [
            " Station",
            " stop",
            " wharf",
            " terminal",
            ", Sydney",
            ", North Sydney",
            ", NSW",
            ", Chatswood"  # 处理特殊情况
        ]
        cleaned = name
        for r in replacements:
            cleaned = cleaned.replace(r, "")
        return cleaned.strip()

    def _find_translation(self, name: str, language_code: str) -> Optional[str]:
        """在所有翻译中查找站名的翻译"""
        if name in self.all_translations:
            return self.all_translations[name].get(language_code)
        return None

    def _translate_station_name(self, 
                              station_name: str, 
                              transport_mode: str, 
                              language_code: str) -> str:
        """翻译单个站台名称"""
        logger.debug(f"Translating station name: '{station_name}' for mode: '{transport_mode}' to language: '{language_code}'")
        
        # 如果语言代码是英文或翻译数据不存在，返回原始名称
        if language_code == "en":
            return station_name

        # 处理包含平台信息的站名
        # 例如: "Chatswood Station, Platform 4, Chatswood" -> ["Chatswood Station", "Platform 4", "Chatswood"]
        parts = [part.strip() for part in station_name.split(',')]
        
        translated_parts = []
        for part in parts:
            # 处理站台信息
            if "Platform" in part or "platform" in part:
                platform_num = ''.join(filter(str.isdigit, part))
                translated_part = f"站台{platform_num}" if language_code == "zh" else part
                translated_parts.append(translated_part)
                continue
                
            # 清理并翻译站名
            clean_name = self._clean_station_name(part)
            original_has_station = "Station" in part
            
            # 尝试查找翻译
            translation = None
            # 首先在指定的交通模式中查找
            if transport_mode in self.translations and clean_name in self.translations[transport_mode]:
                translation = self.translations[transport_mode][clean_name].get(language_code)
                logger.debug(f"Found translation in {transport_mode} mode for '{clean_name}': '{translation}'")
            
            # 如果没找到，在所有翻译中查找
            if not translation:
                translation = self._find_translation(clean_name, language_code)
                if translation:
                    logger.debug(f"Found translation in all modes for '{clean_name}': '{translation}'")
            
            if translation:
                if language_code == "zh" and original_has_station:
                    translation += "站"
                translated_parts.append(translation)
            else:
                logger.warning(f"No translation found for '{clean_name}' in any mode")
                translated_parts.append(part)

        # 始终使用英文逗号作为分隔符
        result = ", ".join(translated_parts)
        logger.debug(f"Final translation: '{result}'")
        return result

    def translate_station_names(self, 
                              station_name: str, 
                              transport_mode: str, 
                              language_code: str = "en") -> str:
        """
        翻译站台名称
        
        Args:
            station_name: 原始站台名称
            transport_mode: 交通工具类型
            language_code: 目标语言代码 (默认: "en")
            
        Returns:
            翻译后的站台名称
        """
        if not station_name:
            return station_name

        # 验证language_code是否支持，如果不支持则使用英文
        if language_code not in self.available_languages:
            logger.warning(f"Unsupported language code: {language_code}, falling back to 'en'")
            language_code = "en"

        if language_code == "en":
            return station_name

        transport_type = self._get_transport_mode(transport_mode)
        if not transport_type:
            logger.warning(f"Unsupported transport mode: {transport_mode}")
            return station_name

        return self._translate_station_name(station_name, transport_type, language_code) 
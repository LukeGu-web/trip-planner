from app.services.tfnsw_service import TfnswService

def get_tfnsw_service() -> TfnswService:
    """
    Get TFNSW service instance
    
    Returns:
        TfnswService: TFNSW service instance
    """
    return TfnswService() 
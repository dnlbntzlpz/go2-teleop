import logging
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    ChannelFactoryInitialize()
    logger.info("✅ ChannelFactoryInitialize completado")
except Exception as e:
    logger.error(f"❌ Error en ChannelFactoryInitialize: {e}")

try:
    client = SportClient()
    client.SetTimeout(10.0)
    client.Init()
    logger.info("✅ SportClient inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error al inicializar SportClient: {e}")

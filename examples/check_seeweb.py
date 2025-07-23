from sky.utils import registry
from sky.clouds.cloud import CloudCapability

cloud = registry.CLOUD_REGISTRY.from_str('seeweb')
ok, reason = cloud.check_credentials(CloudCapability.COMPUTE)
if ok:
    print("Seeweb credentials OK! ✅")
else:
    print(f"Seeweb credentials ERROR: {reason}") 
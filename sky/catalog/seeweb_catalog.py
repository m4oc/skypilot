"""Seeweb service catalog.

This module loads the service catalog file and can be used to
query instance types and pricing information for Seeweb.
"""

import typing
import os
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

from sky.catalog import common
from sky.utils import resources_utils
from sky.utils import ux_utils

if typing.TYPE_CHECKING:
    from sky.clouds import cloud

# Use custom catalog path for Seeweb
custom_catalog_path = os.path.expanduser('~/.SeewebSky/seeweb/vms.csv')
print(f"[DEBUG_SEEWEB_CATALOG181] Loading catalog from: {custom_catalog_path}")
print(f"[DEBUG_SEEWEB_CATALOG182] File exists: {os.path.exists(custom_catalog_path)}")

def clean_gpu_name(gpu_name: str) -> str:
    """Clean GPU name by replacing spaces with hyphens for SkyPilot compatibility."""
    if not gpu_name or pd.isna(gpu_name):
        return ''
    return str(gpu_name).replace(' ', '-')

def clean_accelerator_names_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean accelerator names in the DataFrame by replacing spaces with underscores."""
    if 'AcceleratorName' in df.columns:
        df = df.copy()
        df['AcceleratorName'] = df['AcceleratorName'].apply(clean_gpu_name)
    return df

try:
    _df = pd.read_csv(custom_catalog_path)
    print(f"[DEBUG_SEEWEB_CATALOG183] Successfully loaded CSV with {len(_df)} rows")
    print(f"[DEBUG_SEEWEB_CATALOG184] Columns: {list(_df.columns)}")
    # Clean accelerator names
    _df = clean_accelerator_names_in_df(_df)
    print(f"[DEBUG_SEEWEB_CATALOG185] Full catalog:")
    print(_df)
except Exception as e:
    print(f"[DEBUG_SEEWEB_CATALOG186] Error loading CSV: {e}")
    # Create empty DataFrame as fallback
    _df = pd.DataFrame()
    print(f"[DEBUG_SEEWEB_CATALOG187] Created empty DataFrame as fallback")


def instance_type_exists(instance_type: str) -> bool:
    print(f"[DEBUG_SEEWEB_CATALOG188] instance_type_exists called with: {instance_type}")
    result = common.instance_type_exists_impl(_df, instance_type)
    print(f"[DEBUG_SEEWEB_CATALOG189] instance_type_exists returned: {result}")
    return result


def validate_region_zone(
        region: Optional[str],
        zone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    print(f"[DEBUG_SEEWEB_CATALOG190] validate_region_zone called with:")
    print(f"  region: {region}")
    print(f"  zone: {zone}")
    
    if zone is not None:
        print(f"[DEBUG_SEEWEB_CATALOG191] zone is not None, raising ValueError")
        with ux_utils.print_exception_no_traceback():
            raise ValueError('Seeweb does not support zones.')
    
    result = common.validate_region_zone_impl('Seeweb', _df, region, zone)
    print(f"[DEBUG_SEEWEB_CATALOG192] validate_region_zone returned: {result}")
    return result


def get_hourly_cost(instance_type: str,
                    use_spot: bool = False,
                    region: Optional[str] = None,
                    zone: Optional[str] = None) -> float:
    """Returns the cost, or the cheapest cost among all zones for spot."""
    print(f"[DEBUG_SEEWEB_CATALOG193] get_hourly_cost called with:")
    print(f"  instance_type: {instance_type}")
    print(f"  use_spot: {use_spot}")
    print(f"  region: {region}")
    print(f"  zone: {zone}")
    
    if zone is not None:
        print(f"[DEBUG_SEEWEB_CATALOG194] zone is not None, raising ValueError")
        with ux_utils.print_exception_no_traceback():
            raise ValueError('Seeweb does not support zones.')
    
    result = common.get_hourly_cost_impl(_df, instance_type, use_spot, region, zone)
    print(f"[DEBUG_SEEWEB_CATALOG195] get_hourly_cost returned: {result}")
    return result


def get_vcpus_mem_from_instance_type(
        instance_type: str) -> Tuple[Optional[float], Optional[float]]:
    print(f"[DEBUG_SEEWEB_CATALOG196] get_vcpus_mem_from_instance_type called with: {instance_type}")
    result = common.get_vcpus_mem_from_instance_type_impl(_df, instance_type)
    print(f"[DEBUG_SEEWEB_CATALOG197] get_vcpus_mem_from_instance_type returned: {result}")
    return result


def get_default_instance_type(cpus: Optional[str] = None,
                              memory: Optional[str] = None,
                              disk_tier: Optional[
                                  resources_utils.DiskTier] = None,
                              region: Optional[str] = None,
                              zone: Optional[str] = None) -> Optional[str]:
    print(f"[DEBUG_SEEWEB_CATALOG198] get_default_instance_type called with:")
    print(f"  cpus: {cpus}")
    print(f"  memory: {memory}")
    print(f"  disk_tier: {disk_tier}")
    print(f"  region: {region}")
    print(f"  zone: {zone}")
    
    del disk_tier  # unused
    result = common.get_instance_type_for_cpus_mem_impl(_df, cpus, memory, region, zone)
    print(f"[DEBUG_SEEWEB_CATALOG199] get_default_instance_type returned: {result}")
    return result


def get_accelerators_from_instance_type(
        instance_type: str) -> Optional[Dict[str, int]]:
    print(f"[DEBUG_SEEWEB_CATALOG200] get_accelerators_from_instance_type called with: {instance_type}")
    
    # Filter the dataframe for the specific instance type
    df_filtered = _df[_df['InstanceType'] == instance_type]
    if df_filtered.empty:
        print(f"[DEBUG_SEEWEB_CATALOG201] no instance type found: {instance_type}")
        return None
    
    # Get the first row (all rows for same instance type should have same accelerator info)
    row = df_filtered.iloc[0]
    acc_name = row['AcceleratorName']
    acc_count = row['AcceleratorCount']
    
    # Check if the instance has accelerators
    if pd.isna(acc_name) or pd.isna(acc_count) or acc_name == '' or acc_count == '':
        print(f"[DEBUG_SEEWEB_CATALOG202] no accelerators for instance type: {instance_type}")
        return None
    
    # Convert accelerator count to int/float
    try:
        if int(acc_count) == acc_count:
            acc_count = int(acc_count)
        else:
            acc_count = float(acc_count)
    except (ValueError, TypeError):
        print(f"[DEBUG_SEEWEB_CATALOG203] invalid accelerator count: {acc_count}")
        return None
    
    result = {acc_name: acc_count}
    print(f"[DEBUG_SEEWEB_CATALOG204] get_accelerators_from_instance_type returned: {result}")
    return result


def get_instance_type_for_accelerator(
        acc_name: str,
        acc_count: int,
        cpus: Optional[str] = None,
        memory: Optional[str] = None,
        use_spot: bool = False,
        region: Optional[str] = None,
        zone: Optional[str] = None) -> Tuple[Optional[List[str]], List[str]]:
    """
    Restituisce i dati per l'elenco finale che 
    arriva all'utente.
    """
    print(f"[DEBUG_SEEWEB_CATALOG202] get_instance_type_for_accelerator called with:")
    print(f"  acc_name: {acc_name}")
    print(f"  acc_count: {acc_count}")
    print(f"  cpus: {cpus}")
    print(f"  memory: {memory}")
    print(f"  use_spot: {use_spot}")
    print(f"  region: {region}")
    print(f"  zone: {zone}")
    
    if zone is not None:
        print(f"[DEBUG_SEEWEB_CATALOG203] zone is not None, raising ValueError")
        with ux_utils.print_exception_no_traceback():
            raise ValueError('Seeweb does not support zones.')
    
    result = common.get_instance_type_for_accelerator_impl(df=_df,
                                                         acc_name=acc_name,
                                                         acc_count=acc_count,
                                                         cpus=cpus,
                                                         memory=memory,
                                                         use_spot=use_spot,
                                                         region=region,
                                                         zone=zone)
    print(f"[DEBUG_SEEWEB_CATALOG204] get_instance_type_for_accelerator returned: {result}")
    return result

def regions() -> List['cloud.Region']:
    print(f"[DEBUG_SEEWEB_CATALOG205] regions() called")
    result = common.get_region_zones(_df, use_spot=False)
    print(f"[DEBUG_SEEWEB_CATALOG206] regions() returned: {result}")
    return result


def get_region_zones_for_instance_type(instance_type: str,
                                       use_spot: bool = False) -> List['cloud.Region']:
    print(f"[DEBUG_SEEWEB_CATALOG207] get_region_zones_for_instance_type called with:")
    print(f"  instance_type: {instance_type}")
    print(f"  use_spot: {use_spot}")
    
    df = _df[_df['InstanceType'] == instance_type]
    region_list = common.get_region_zones(df, use_spot)
    
    # Hack: Enforce hierarchical region priority
    # Priority order: 1. Frosinone (it-fr2), 2. Milano (it-mi2), 3. Lugano (ch-lug1), 4. Bulgaria (bg-sof1)
    priority_regions = ['it-fr2', 'it-mi2', 'ch-lug1', 'bg-sof1']
    prioritized_regions = []
    other_regions = []
    
    # First, add regions in priority order if they exist
    for priority_region in priority_regions:
        for region in region_list:
            if region.name == priority_region:
                prioritized_regions.append(region)
                break
    
    # Then, add any remaining regions that weren't in the priority list
    for region in region_list:
        if region.name not in priority_regions:
            other_regions.append(region)
    
    result = prioritized_regions + other_regions
    print(f"[DEBUG_SEEWEB_CATALOG208] get_region_zones_for_instance_type returned: {result}")
    return result


def list_accelerators(
        gpus_only: bool,
        name_filter: Optional[str],
        region_filter: Optional[str],
        quantity_filter: Optional[int],
        case_sensitive: bool = True,
        all_regions: bool = False,
        require_price: bool = True) -> Dict[str, List[common.InstanceTypeInfo]]:
    print(f"[DEBUG_SEEWEB_CATALOG209] list_accelerators called with:")
    print(f"  gpus_only: {gpus_only}")
    print(f"  name_filter: {name_filter}")
    print(f"  region_filter: {region_filter}")
    print(f"  quantity_filter: {quantity_filter}")
    print(f"  case_sensitive: {case_sensitive}")
    print(f"  all_regions: {all_regions}")
    print(f"  require_price: {require_price}")
    
    result = common.list_accelerators_impl('Seeweb', _df, gpus_only, name_filter, region_filter,
                                          quantity_filter, case_sensitive, all_regions)
    print(f"[DEBUG_SEEWEB_CATALOG210] list_accelerators returned: {result}")
    return result
import hashlib
import json
from pathlib import Path

import pydantic
from Crypto.Cipher import AES

# The mysterious and magical password used to encrypt all save files
save_file_password = b"lcslime14a5"


class SaveFile(pydantic.BaseModel): ...


"""
[
    "VehicleWarrantyTicket",
    # "ShipUnlockStored_Romantic table",
    "GroupCredits",
    "QuotasPassed",
    # "ShipUnlockStored_JackOLantern",
    "Stats_DaysSpent",
    "FileGameVers",
    # "ShipUnlockStored_Goldfish",
    "QuotaFulfilled",
    # "ShipUnlockStored_Toilet",
    "UnlockedShipObjects",
    # "ShipUnlockStored_Plushie pajama man",
    "CurrentPlanetID",
    # "ShipUnlockStored_Disco Ball",
    # "ShipUnlockStored_Table",
    # "ShipUnlockStored_Record player",
    # "ShipUnlockStored_File Cabinet",
    "Stats_Deaths",
    # "ShipUnlockStored_Shower",
    "Stats_StepsTaken",
    # "ShipUnlockStored_Loud horn",
    # "ShipUnlockStored_Signal translator",
    # "ShipUnlockStored_Cupboard",
    "StoryLogs",
    # "ShipUnlockStored_Teleporter",
    # "ShipUnlockStored_Inverse Teleporter",
    "Stats_ValueCollected",
    "RandomSeed",
    "DeadlineTime",
    # "ShipUnlockStored_Bunkbeds",
    # "ShipUnlockStored_Television",
    "Alias_BetterSaves",
    "ProfitQuota",
]
"""

"""
STILL NEED TO PARSE OUT THE VALUE FROM THIS:
{'__type': 'System.Int32[],mscorlib', 'value': [0, 7, 8, 11, 15, 16]}
{'__type': 'int', 'value': 10}
vehicle_warranty_ticket: bool = pydantic.Field(validation_alias="VehicleWarrantyTicket")
group_credits: int = pydantic.Field(validation_alias="GroupCredits")
quotas_passed: int = pydantic.Field(validation_alias="QuotasPassed")
stats_days_spent: int = pydantic.Field(validation_alias="Stats_DaysSpent")
file_game_vers: int = pydantic.Field(validation_alias="FileGameVers")
quota_fulfilled: int = pydantic.Field(validation_alias="QuotaFulfilled")
unlocked_ship_objects: System.Int32[],mscorlib = pydantic.Field(validation_alias="UnlockedShipObjects")
current_planet_id: int = pydantic.Field(validation_alias="CurrentPlanetID")
stats_deaths: int = pydantic.Field(validation_alias="Stats_Deaths")
stats_steps_taken: int = pydantic.Field(validation_alias="Stats_StepsTaken")
story_logs: System.Int32[],mscorlib = pydantic.Field(validation_alias="StoryLogs")
stats_value_collected: int = pydantic.Field(validation_alias="Stats_ValueCollected")
random_seed: int = pydantic.Field(validation_alias="RandomSeed")
deadline_time: int = pydantic.Field(validation_alias="DeadlineTime")
alias_better_saves: string = pydantic.Field(validation_alias="Alias_BetterSaves")
profit_quota: int = pydantic.Field(validation_alias="ProfitQuota")
"""


def strip_non_printable(value: str) -> str:
    return "".join(character for character in value if character.isprintable())


def decrypt_save(save_file_location: Path) -> dict:
    """
    Decrypts a Lethal Company save file so we can read the BetterSaves metadata
    """
    encrypted_data = save_file_location.read_bytes()
    salt = encrypted_data[:16]

    key = hashlib.pbkdf2_hmac("sha1", save_file_password, salt, 100, 16)
    cipher = AES.new(key, AES.MODE_CBC, salt)

    return json.loads(strip_non_printable(cipher.decrypt(encrypted_data[16:]).decode()))

import enum
import typing


class MoonCosts(enum.IntEnum):
    Experimentation = 0
    Assurance = 0
    Vow = 0
    Offense = 0
    March = 0
    Adamance = 0
    Rend = 550
    Dine = 600
    Titan = 700
    Artifice = 1500
    Embrion = 150


class Versions(enum.StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    v35 = enum.auto()
    v36 = enum.auto()
    v37 = enum.auto()
    v38 = enum.auto()
    v40 = enum.auto()
    v45 = enum.auto()
    v47 = enum.auto()
    v48 = enum.auto()
    v49 = enum.auto()
    v50 = enum.auto()
    v55 = enum.auto()
    v56 = enum.auto()
    v61 = enum.auto()
    v64 = enum.auto()
    v65 = enum.auto()
    v66 = enum.auto()
    v67 = enum.auto()
    v68 = enum.auto()
    v69 = enum.auto()
    v70 = enum.auto()
    v71 = enum.auto()
    v72 = enum.auto()
    v73 = enum.auto()
    v80 = enum.auto()


class Dungeons(enum.IntEnum):
    facility = 1
    mansion = 2
    facility_3_fire = 4
    mineshaft = 5


class Weathers(enum.IntEnum):
    clear = 0
    rainy = 1
    stormy = 2
    foggy = 3
    flooded = 4
    eclipsed = 5


ItemTypesLiteral = typing.Literal[
    "Airhorn",
    "Big bolt",
    "Bone",
    "Bottles",
    "Brass bell",
    "Candy",
    "Cash register",
    "Chemical jug",
    "Clock",
    "Clown horn",
    "Comedy",
    "Control pad",
    "Cookie mold pan",
    "DIY-Flashbang",
    "Dust pan",
    "Ear",
    "Easter egg",
    "Egg beater",
    "Fancy lamp",
    "Flask",
    "Foot",
    "Garbage lid",
    "Gift Box",
    "Gold bar",
    "Golden cup",
    "Hair brush",
    "Hairdryer",
    "Hand",
    "Heart",
    "Jar of pickles",
    "Knee",
    "Large axle",
    "Laser pointer",
    "Magic 7 ball",
    "Magnifying glass",
    "Metal sheet",
    "Mug",
    "Old phone",
    "Painting",
    "Perfume bottle",
    "Pill bottle",
    "Plastic cup",
    "Plastic fish",
    "Red soda",
    "Remote",
    "Ribcage",
    "Ring",
    "Robot toy",
    "Rubber Ducky",
    "Soccer ball",
    "Steering wheel",
    "Stop sign",
    "Tea kettle",
    "Teeth",
    "Toilet paper",
    "Tongue",
    "Toothpaste",
    "Toy cube",
    "Toy train",
    "Tragedy",
    "V-type engine",
    "Whoopie-Cushion",
    "Yield sign",
    "Zed Dog",
    "",
]
InfestationTypesLiteral = typing.Literal["nutcracker", "lootbug", ""]
MoonTypesLiteral = typing.Literal[
    "Experimentation",
    "Assurance",
    "Vow",
    "Offense",
    "March",
    "Adamance",
    "Rend",
    "Dine",
    "Titan",
    "Artifice",
    "Embrion",
    "",
]
WeatherTypesLiteral = typing.Literal[
    "clear", "stormy", "rainy", "flooded", "eclipsed", "foggy"
]
LayoutTypesLiteral = typing.Literal["facility", "mansion", "mineshaft", ""]
RunTypesLiteral = typing.Literal["smhq", "hq", "10q"]

HazardTypesLiteral = typing.Literal["turret", "landmine", "spike trap"]

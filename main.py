#!/usr/bin/env python3
import copy
import datetime
import math
import random
import statistics
import sys
import textwrap
import typing
from collections.abc import Callable
from pathlib import Path
from statistics import StatisticsError
from typing import Annotated, NamedTuple, get_args

import click
import iterfzf
import pydantic
import pydantic_typer
import pydantic_yaml
import typer
import xdg_base_dirs
from typer.models import OptionInfo

import sell
from sell.calculator import calculate_overtime_sell

# No idea where 0.51270322870301 comes from, but if Maku thinks it works then so do I.
spooky_guoda_number = 0.51270322870301


def flatten_args(func: Callable) -> Callable:
    """Flatten command line arguments to the underling pydantic class field names."""
    if hasattr(func, "__annotations__"):
        for value in func.__annotations__.values():
            function_args = get_args(value)
            option_info = next(
                (arg for arg in function_args if isinstance(arg, OptionInfo)), None
            )
            qualifiers = next(
                (arg for arg in function_args if isinstance(arg, list)), None
            )
            if option_info is not None and qualifiers is not None:
                option_info.default = f"--{qualifiers[-1].replace('_', '-')}"

    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def reverse_quota_curve(
    previous_quota_count: int, current_quota: int, previous_quota: int
) -> float:
    # Adapted from Maku's glorious MakuSheet. I don't get how it works, but _god damn_ does it work.
    r_value = (
        (current_quota - previous_quota) / 100 / (1 + (previous_quota_count**2) / 16)
    ) - 1

    if r_value <= -0.1302:
        roll = (
            -0.160907593946605
            * pow(
                -r_value
                + pow(
                    pow(-r_value - 0.120329719101165, 2) + 5.84171028339325 * 0.00001,
                    0.5,
                )
                - 0.120329719101165,
                1 / 3,
            )
            + 0.140363846903451
            + 0.00624342950447879
            / pow(
                -r_value
                + pow(
                    pow(-r_value - 0.120329719101165, 2) + 5.84171028339325 * 0.00001,
                    0.5,
                )
                - 0.120329719101165,
                1 / 3,
            )
        )

    elif r_value <= 0.1534:
        roll = (
            -0.955441906274132
            * pow(
                -r_value
                + pow(pow(0.0183063044253273 - r_value, 2) + 0.00616352354339119, 0.5)
                + 0.0183063044253273,
                1 / 3,
            )
            + 0.511256642996555
            + 0.175178433678035
            / pow(
                -r_value
                + pow(pow(0.0183063044253273 - r_value, 2) + 0.00616352354339119, 0.5)
                + 0.0183063044253273,
                1 / 3,
            )
        )
    else:
        roll = (
            -0.160571168650179
            * pow(
                -r_value
                + pow(pow(0.146192009650422 - r_value, 2) + 0.000100776549962117, 0.5)
                + 0.146192009650422,
                1 / 3,
            )
            + 0.864861513055629
            + 0.00747229593834329
            / pow(
                -r_value
                + pow(pow(0.146192009650422 - r_value, 2) + 0.000100776549962117, 0.5)
                + 0.146192009650422,
                1 / 3,
            )
        )

    return min(max(0.0001, roll), 0.9999)


def quota_curve(r_value: float) -> float:
    """
    Generates a quota curve for a given r value. We only use this when calculating the chance we'll reach
    a particular quota amount, since pace calculations want to use the absolute midroll in all cases.
    """
    if r_value <= 0.1172:
        return (
            (120.0163409 * r_value - 50.5378659) * r_value + 7.4554
        ) * r_value - 0.503
    elif r_value <= 0.8804:
        return (
            (0.57326727 * r_value - 0.8792601) * r_value + 0.73737564
        ) * r_value - 0.20546592
    else:
        return (
            (120.77228959 * r_value - 313.35391533) * r_value + 271.4424619
        ) * r_value - 78.35783615


def increment_quota(quota_number: int, r_value: float) -> int:
    return math.floor(
        100 * (1 + quota_number * quota_number / 16) * (1 + quota_curve(r_value))
    )


def calculate_quota_chance(
    wanted_credits: int,
    target_quota_amount: int,
    current_quota_amount: int,
    current_quota_number: int,
    current_ship_loot: int,
    current_average: int,
    quota_days_played: int,
) -> float:
    iterations: int = int(1e5)
    successful_iterations: int = 0
    for i in range(iterations):
        total: int = 0
        previous_quota_amount: int = -1
        quota_amount = current_quota_amount
        quota_number = current_quota_number
        days_to_play = 0 - quota_days_played
        while current_ship_loot + current_average * days_to_play >= total:
            total += calculate_overtime_sell(wanted_credits, quota_amount)
            previous_quota_amount = quota_amount
            quota_amount += increment_quota(quota_number, random.random())
            quota_number += 1
            days_to_play += 3
        if previous_quota_amount >= target_quota_amount:
            successful_iterations += 1

    return successful_iterations / iterations


WeatherTypesLiteral = typing.Literal[
    "clear", "stormy", "rainy", "flooded", "eclipsed", "foggy"
]

WeatherTypes = Annotated[
    str,
    typer.Option(
        help="The weather for the day",
        click_type=click.Choice(WeatherTypesLiteral.__args__),
    ),
]
MoonTypesLiteral = typing.Literal[
    "experimentation",
    "assurance",
    "vow",
    "offense",
    "march",
    "adamance",
    "rend",
    "dine",
    "titan",
    "artifice",
    "embrion",
]
MoonTypes = Annotated[
    str,
    typer.Option(
        help="The moon being landed on",
        click_type=click.Choice(MoonTypesLiteral.__args__),
    ),
]
LayoutTypesLiteral = typing.Literal["facility", "mansion", "mineshaft", ""]
LayoutTypes = Annotated[
    str,
    typer.Option(
        help="The interior type",
        click_type=click.Choice(LayoutTypesLiteral.__args__),
    ),
]

RunTypesLiteral = typing.Literal["smhq", "hq"]
RunTypes = Annotated[
    str,
    typer.Option(
        help="The type of run",
        click_type=click.Choice(RunTypesLiteral.__args__),
        default="hq",
    ),
]


class QuotaRollRange(NamedTuple):
    minimum: int
    average: int
    maximum: int


class Day(pydantic.BaseModel):
    moon: MoonTypes = "experimentation"
    weather: WeatherTypes = "clear"
    item_count: Annotated[
        int, typer.Option(help="The number of items scanned for (excluding bees)")
    ] = 0
    bee_count: Annotated[
        int, typer.Option(help="The number of bees/eggs scanned for")
    ] = 0
    collected_count: Annotated[
        int, typer.Option(help="The number of items collected at the end of the day")
    ] = 0
    top_line: Annotated[
        int, typer.Option(help="The top line on the results screen")
    ] = 0
    bottom_line: Annotated[
        int, typer.Option(help="The bottom line on the results screen")
    ] = 0
    layout: LayoutTypes = ""


class Quota(pydantic.BaseModel):
    days: list[Day] = pydantic.Field(default_factory=list)
    amount: int = 0
    sold: int = 0
    roll: float | None = None
    r_value: float | None = None
    number: int
    is_projected: bool = False

    def add_day(self, day: Day) -> None:
        self.days.append(day)

    @property
    def total_collected(self) -> int:
        return sum((day.top_line for day in self.days))

    @property
    def on_ship(self) -> int:
        return self.total_collected - self.sold

    @property
    def days_played(self) -> int:
        return len(self.days)

    @property
    def next_quota_roll_range(self) -> QuotaRollRange:
        # The spooky magic numbers here were nabbed from Maku's glorious spreadsheet.
        minimum_roll = (
            math.floor((100 * (1 + (self.number**2) / 16) * (1 - 0.503))) + self.amount
        )
        average_roll = (
            math.floor((100 * (1 + (self.number**2) / 16) * 1.015244)) + self.amount
        )
        maximum_roll = (
            math.floor((100 * (1 + (self.number**2) / 16) * (1 + 0.503))) + self.amount
        )
        return QuotaRollRange(minimum_roll, average_roll, maximum_roll)

    def calculate_r_value_and_roll(self, previous_amount) -> tuple[float, float]:
        r_value = (
            (self.amount - previous_amount) / 100 / (1 + ((self.number - 1) ** 2) / 16)
        ) - 1
        roll = min(max((r_value + 0.503) / 1.006, 0), 1)
        return r_value, roll


class Run(pydantic.BaseModel):
    quotas: list[Quota] = pydantic.Field(
        default_factory=lambda: [
            Quota(days=[], amount=130, sold=0, roll=spooky_guoda_number, number=1)
        ]
    )
    run_date: datetime.datetime = pydantic.Field(default_factory=datetime.datetime.now)
    run_title: str = ""
    run_type: RunTypes = "hq"
    wiped: bool = False
    version: str = "v73"
    players: set[str] = pydantic.Field(default_factory=set)
    target_quota: int = 21

    @staticmethod
    def get_run_file() -> Path:
        if not current_run_file.exists():
            return sorted(list(run_directory.glob("*")))[-1]
        current_run = pydantic_yaml.parse_yaml_file_as(CurrentRun, current_run_file)
        if not current_run.current_run.exists():
            raise RuntimeError(f"Current run does not exist: {current_run_file}")
        return current_run.current_run

    @classmethod
    def get_run(cls) -> "Run":
        run_file = cls.get_run_file()
        return pydantic_yaml.parse_yaml_file_as(cls, run_file)

    @property
    def quota_count(self) -> int:
        return len(self.quotas) + 1

    @property
    def current_quota_number(self) -> int:
        return self.quotas[-1].number

    @property
    def on_ship(self) -> int:
        return sum((quota.on_ship for quota in self.quotas))

    @property
    def sum_total_collected(self) -> int:
        return sum((quota.total_collected for quota in self.quotas))

    @property
    def sum_total_sold(self) -> int:
        return sum((quota.sold for quota in self.quotas))

    @property
    def day_count(self) -> int:
        return sum((quota.days_played for quota in self.quotas))

    @property
    def current_quota_amount(self) -> int:
        return self.quotas[-1].amount

    @property
    def efficiency(self) -> float:
        if self.day_count == 0:
            return float("NaN")
        return self.get_average_top_line(1) / self.get_average_bottom_line(1)

    def get_average_top_line(
        self, fromq: int, quotas: list[Quota] | None = None
    ) -> int:
        if quotas is None:
            quotas = self.quotas
        fromq = max(fromq, 1)
        fromq -= 1
        top_lines = [day.top_line for quota in quotas[fromq:] for day in quota.days]
        return int(round(statistics.mean(top_lines), 0))

    def get_average_bottom_line(
        self, fromq: int, quotas: list[Quota] | None = None
    ) -> int:
        if quotas is None:
            quotas = self.quotas
        fromq = max(fromq, 1)
        fromq -= 1
        bottom_lines = [
            day.bottom_line for quota in quotas[fromq:] for day in quota.days
        ]
        return int(round(statistics.mean(bottom_lines), 0))

    @property
    def pace(self, max_quota=30) -> tuple[int, int]:
        quotas = self.project_quotas(max_quota)
        # The predicted amount of money on ship for each quota
        projected_on_ship_amounts = [quotas[0].total_collected]
        if self.current_quota_number == 1:
            return quotas[0].total_collected, 1
        pace_average = self.get_average_top_line(self.fromq, quotas)
        previous_sold = quotas[0].sold
        max_quota_amount = quotas[0].amount
        max_quota_number = 1
        amount_on_ship = quotas[0].on_ship
        for quota in quotas[1:]:
            amount_on_ship += quota.total_collected
            if not quota.is_projected:
                projected_on_ship_amounts.append(amount_on_ship)
                amount_on_ship -= quota.sold
                continue
            previous_projected = projected_on_ship_amounts[-1]

            if (
                projected_on_ship := previous_projected
                - previous_sold
                + (pace_average * 3)
            ) >= quota.amount:
                projected_on_ship_amounts.append(projected_on_ship)
                previous_sold = quota.sold
                max_quota_amount = quota.amount
                max_quota_number = quota.number
            else:
                return quota.amount, quota.number
        return max_quota_amount, max_quota_number

    @property
    def needed_average(self) -> int:
        quotas = self.project_quotas(self.target_quota)
        amount_needed = sum((quota.sold for quota in quotas)) - self.sum_total_collected
        if amount_needed < 0:
            return 0
        return math.ceil(amount_needed / (self.target_quota * 3 - self.day_count))

    @property
    def fromq(self) -> int:
        if self.run_type == "hq":
            return 2
        return 1

    def project_quotas(self, quota_number: int) -> list[Quota]:
        """
        Use spooky Maku magic to predict the future
        """
        quotas = copy.deepcopy(self.quotas)
        if len(self.quotas) >= quota_number:
            return quotas
        last_quota = quotas[-1]
        average_top_line = self.get_average_top_line(self.fromq)
        average_bottom_line = self.get_average_bottom_line(self.fromq)
        if last_quota.sold == 0:
            last_quota.sold = calculate_overtime_sell(1500, last_quota.amount)
        if len(last_quota.days) < 3:
            last_quota.is_projected = True
        for _ in range(3 - len(last_quota.days)):
            last_quota.days.append(
                Day(top_line=average_top_line, bottom_line=average_bottom_line)
            )
        for quota in range(quotas[-1].number, quota_number):
            roll_range = quotas[-1].next_quota_roll_range
            next_average_amount = int(
                round(
                    (
                        (1 - spooky_guoda_number) * roll_range.minimum
                        + spooky_guoda_number * roll_range.maximum
                    ),
                    0,
                )
            )
            new_quota = Quota(
                days=[
                    Day(top_line=average_top_line, bottom_line=average_bottom_line)
                    for _ in range(3)
                ],
                amount=next_average_amount,
                number=quota + 1,
                sold=calculate_overtime_sell(1500, next_average_amount),
                is_projected=True,
            )
            new_quota.r_value, new_quota.roll = new_quota.calculate_r_value_and_roll(
                quotas[-1].amount
            )
            quotas.append(new_quota)
        return quotas

    def add_quota(self, amount: int, sold: int) -> None:
        quota = Quota(days=[], amount=amount, sold=sold, number=len(self.quotas) + 1)
        quota.r_value, quota.roll = quota.calculate_r_value_and_roll(
            self.quotas[-1].amount
        )
        self.quotas.append(quota)

    def update_quota(self, amount: int | None, sold: int | None) -> None:
        kwargs = {}
        if amount is not None:
            kwargs["amount"] = amount
        if sold is not None:
            kwargs["sold"] = sold
        old_quota = self.quotas[-1]
        quota = Quota(days=[], number=old_quota.number, is_projected=False, **kwargs)
        base = old_quota.model_dump(
            exclude_defaults=True, exclude_unset=True, exclude_none=True
        )
        new_data = quota.model_dump(
            exclude_defaults=True, exclude_none=True, exclude_unset=True
        )
        quota = quota.model_validate({**base, **new_data})
        if quota.number != 1:
            quota.r_value, quota.roll = quota.calculate_r_value_and_roll(
                self.quotas[-2].amount
            )
        self.quotas[-1] = quota

    def add_day(self, day: Day) -> None:
        self.quotas[-1].days.append(day)

    def get_quota_roll(self, quota_number: int | None) -> float:
        if quota_number is None:
            quota_number = self.current_quota_number
        else:
            quota_number = max(quota_number, 2)
        if len(self.quotas) < quota_number:
            raise IndexError(
                f"quota {quota_number} has not happened yet, we're only up to {len(self.quotas)}"
            )
        roll = self.quotas[quota_number - 1].roll
        assert roll is not None
        return roll

    def get_revq_quota_roll(self, quota_number: int | None) -> float:
        if quota_number is None:
            quota_number = self.current_quota_number
        else:
            quota_number = max(quota_number, 2)
        if len(self.quotas) < quota_number:
            raise IndexError(
                f"quota {quota_number} has not happened yet, we're only up to {len(self.quotas)}"
            )
        previous_quota_number = quota_number - 1
        quota_index = quota_number - 1
        previous_quota_index = quota_index - 1
        quota_value = self.quotas[quota_index].amount
        previous_quota_value = self.quotas[previous_quota_index].amount
        return reverse_quota_curve(
            previous_quota_number, quota_value, previous_quota_value
        )

    def write_run(self):
        pydantic_yaml.to_yaml_file(self.get_run_file(), self)

    def quota_chance(
        self, target_quota_amount: int, wanted_credits: int = 1500
    ) -> float:
        return calculate_quota_chance(
            wanted_credits,
            target_quota_amount,
            self.current_quota_amount,
            self.current_quota_number,
            self.on_ship,
            self.get_average_top_line(self.fromq),
            self.quotas[-1].days_played,
        )

    def printable(self) -> str:
        """Too lazy to deal with altering pydantic repr (assuming it's not just def __repr__(self):), so we're just doing this."""
        return f"{self.run_date}|{self.version}|{', '.join(self.players)}|{self.run_title}|Quota {self.current_quota_number}—{self.current_quota_amount}|On ship: {self.on_ship}"


class CurrentRun(pydantic.BaseModel):
    current_run: Path


run_directory = xdg_base_dirs.xdg_state_home() / "sheet-company"
current_run_file = run_directory / "current_run.yaml"

app = pydantic_typer.Typer()


@app.command(help="Lets you pick a previous run to be your current run")
def set_current_run(
    include_wipes: Annotated[
        bool, typer.Option(help="Whether or not to include wipes in the selection")
    ] = False,
):
    runs = []
    for run_file in run_directory.glob("run*.yaml"):
        try:
            run = pydantic_yaml.parse_yaml_file_as(Run, run_file)
            if not include_wipes and run.wiped:
                continue
            runs.append(run)
        except pydantic.ValidationError:
            continue
    titles_and_dates = {run.printable(): run for run in runs}
    selection = iterfzf.iterfzf(titles_and_dates.keys())
    selected_run = titles_and_dates.get(selection)
    if selected_run is None:
        print(
            f"Selected run {selection} somehow doesn't exist. Weep in fear and terror.",
            file=sys.stderr,
        )
        raise typer.Abort()
    run_file = run_directory / f"run-{selected_run.run_date.isoformat()}.yaml"
    current_run = CurrentRun(current_run=run_file)
    pydantic_yaml.to_yaml_file(current_run_file, current_run)


@app.command(help="Starts a new run")
def start_run(
    run_title: Annotated[
        str, typer.Option(help="The title for the run, to be used for future selection")
    ] = "",
    run_type: Annotated[
        str,
        typer.Option(help="The type of run", click_type=click.Choice(["hq", "smhq"])),
    ] = "hq",
    version: Annotated[
        str, typer.Option(help="The version of Lethal Company being played")
    ] = "v73",
    players: Annotated[
        list[str] | None, typer.Option(help="The players in the current run")
    ] = None,
    target_quota_amount: Annotated[
        int,
        typer.Option("--target-quota", help="The quota the current run is targeting"),
    ] = 20,
):
    if not players:
        print("No players set for run.", file=sys.stderr)
        raise typer.Abort()
    run_directory.mkdir(parents=True, exist_ok=True)
    run_date = datetime.datetime.now().astimezone().replace(microsecond=0)
    new_run_file = run_directory / f"run-{run_date.isoformat()}.yaml"
    new_run = Run(
        quotas=[Quota(days=[], amount=130, sold=0, roll=spooky_guoda_number, number=1)],
        run_title=run_title,
        run_date=run_date,
        run_type=run_type,
        version=version,
        players=set(players),
        target_quota=target_quota_amount,
    )
    pydantic_yaml.to_yaml_file(new_run_file, new_run)
    current_run = CurrentRun(current_run=new_run_file)
    pydantic_yaml.to_yaml_file(current_run_file, current_run)


@app.command(help="Updates the currently selected run")
def update_run(
    run_title: Annotated[
        str, typer.Option(help="The title for the run, to be used for future selection")
    ] = "",
    run_type: Annotated[
        str,
        typer.Option(
            help="The type of run", click_type=click.Choice(["hq", "smhq", ""])
        ),
    ] = "",
    version: Annotated[
        str, typer.Option(help="The version of Lethal Company being played")
    ] = "",
    players: Annotated[
        list[str] | None, typer.Option(help="The players in the current run")
    ] = None,
    target_quota_amount: Annotated[
        int | None,
        typer.Option("--target-quota", help="The quota the current run is targeting"),
    ] = None,
    wiped: Annotated[
        bool | None, typer.Option(help="Whether or not the run has wiped")
    ] = None,
):
    run = Run.get_run()
    if run_title:
        run.run_title = run_title
    if run_type:
        run.run_type = run_type
    if version:
        run.version = version
    if players:
        run.players = set(players)
    if target_quota_amount is not None:
        run.target_quota = target_quota_amount
    if wiped is not None:
        run.wiped = wiped
    run.write_run()


@flatten_args
@app.command(help="Adds a new day")
def add_day(day: Annotated[Day, typer.Option()]):
    run = Run.get_run()
    run.add_day(day)
    run.write_run()


@flatten_args
@app.command(help="Updates the current day")
def update_day(day: Annotated[Day, typer.Option()]):
    run = Run.get_run()
    old_day = run.quotas[-1].days[-1]
    base = old_day.model_dump(
        exclude_defaults=True, exclude_none=True, exclude_unset=True
    )
    new_data = day.model_dump(
        exclude_defaults=True, exclude_none=True, exclude_unset=True
    )
    day = day.model_validate({**base, **new_data})
    run.quotas[-1].days[-1] = day
    run.write_run()


AmountOption = typer.Option(
    help="The quota amount rolled at the start of the quota period"
)
SoldOption = typer.Option(help="How much was sold to fulfill the quota")


@flatten_args
@app.command(help="Adds a new quota")
def add_quota(
    amount: Annotated[int, AmountOption] = 0,
    sold: Annotated[int, SoldOption] = 0,
):
    run = Run.get_run()
    run.add_quota(amount=amount, sold=sold)
    run.write_run()


@flatten_args
@app.command(help="Updates the current quota")
def update_quota(
    amount: Annotated[int | None, AmountOption] = None,
    sold: Annotated[int | None, SoldOption] = None,
):
    run = Run.get_run()
    run.update_quota(amount=amount, sold=sold)
    run.write_run()


@app.command(help="Shows how good a quota roll was")
def quota_roll(
    quota: Annotated[
        int | None, typer.Option(help="The quota to calculate the percentage for")
    ] = None,
):
    run = Run.get_run()
    print(f"{int(round(run.get_quota_roll(quota_number=quota) * 100, 0))}%")


@app.command(help="Shows the percentage of the last sold")
def quota_roll_revq(
    quota: Annotated[
        int | None, typer.Option(help="The quota to calculate the percentage for")
    ] = None,
):
    run = Run.get_run()
    print(f"{run.get_revq_quota_roll(quota)}%")


@app.command(help="Shows the average collected value")
def average(
    fromq: Annotated[
        int, typer.Option(help="The first quota to calculate the average from")
    ] = 1,
):
    fromq = max(fromq, 1)
    run = Run.get_run()
    try:
        print(run.get_average_top_line(fromq))
    except StatisticsError:
        print("idk")


@app.command(help="Shows the currently selected run")
def show_current_run():
    run = Run.get_run()
    print(run.printable())


@app.command(help="Shows the average collection efficiency")
def average_efficiency(
    fromq: Annotated[
        int, typer.Option(help="The first quota to calculate the efficiency from")
    ] = 1,
):
    fromq = max(fromq, 1)
    fromq -= 1
    run = Run.get_run()
    try:
        if math.isnan(run.efficiency):
            print("idk")
        else:
            print(f"{round(run.efficiency * 100, 2)}%")
    except StatisticsError:
        print("idk")


@app.command(help="Shows how much loot is currently on ship")
def on_ship():
    run = Run.get_run()
    print(run.on_ship)


@app.command("pace", help="Shows the pace the run is projected to be on")
def get_pace():
    run = Run.get_run()
    try:
        if run.wiped:
            print("wiped")
        else:
            quota_amount, quota_number = run.pace
            print(f"Q{quota_number}: {quota_amount}")
    except StatisticsError:
        print("idk")


@app.command(help="Shows how much loot has been collected in total")
def total_collected(
    quota: Annotated[
        int | None,
        typer.Option(
            help="The quota to show the total for. Leave unset for all quotas"
        ),
    ],
):
    run = Run.get_run()
    if quota is None:
        print(run.sum_total_collected)
        return
    quota = max(quota, 1) - 1
    if not len(run.quotas) > quota:
        print(f"Quota {quota + 1} has not been reached yet.", file=sys.stderr)
        raise typer.Abort()
    print(run.quotas[quota].total_collected)


@app.command(help="Shows the average needed to meet the target quota")
def needed_average():
    run = Run.get_run()
    try:
        print(run.needed_average)
    except StatisticsError:
        print("idk")


@app.command(help="Shows the desired target quota")
def target_quota():
    run = Run.get_run()
    print(run.target_quota)


@app.command(help="Shows how much loot has been collected in total")
def calculate_overtime(
    desired_amount: Annotated[
        int, typer.Argument(help="How much money you want after overtime")
    ],
    quota: Annotated[
        int | None,
        typer.Option(
            help="How much your quota amount is. Leave this blank to use the latest value"
        ),
    ] = None,
):
    run = Run.get_run()
    if quota is None:
        quota = run.current_quota_amount
    sell_amount = calculate_overtime_sell(desired_amount, quota)
    print(
        textwrap.dedent(f"""
    Sell:     {sell_amount}
    OT bonus: {desired_amount - sell_amount}
    """).strip()
    )


@app.command(help="Shows the chance of reaching a given quota amount")
def chance(
    target: Annotated[int, typer.Argument(help="The amount you want to reach")],
    base_sell: Annotated[
        int, typer.Option(help="The minimum amount you need to sell each quota")
    ] = 1500,
    round_place: Annotated[
        int, typer.Option(help="The number of places you want to round to")
    ] = 2,
):
    run = Run.get_run()
    try:
        print(f"{round(run.quota_chance(target, base_sell) * 100, round_place)}%")
    except StatisticsError:
        print("idk")


@app.command(help="Shows a store interface for quickly calculating sell")
def store():
    run = Run.get_run()
    sold_amount = sell.calculator.run(
        quota=run.current_quota_amount, moon_amount=1500, version=run.version
    )
    if sold_amount is not None:
        run.update_quota(amount=None, sold=sold_amount)
        run.write_run()


if __name__ == "__main__":
    app()

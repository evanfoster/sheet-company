import asyncio
import collections
import json
import math
import typing
from pathlib import Path

import asyncinotify
import pyperclip
import xdg_base_dirs
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Digits,
    Footer,
    Label,
    ListItem,
    ListView,
)

cache_directory = xdg_base_dirs.xdg_cache_home() / "sheet-company"


class StoreItem(typing.NamedTuple):
    quantity: int
    sale_percentage: int
    item_name: str
    sale_price: float | int
    original_price: int


class StoreItemList(collections.UserList):
    max_length = 12
    data: list[StoreItem]

    def __len__(self) -> int:
        return sum(item.quantity for item in self.data)

    @property
    def sell_commands(self) -> list[str]:
        output = []
        for item in self.data:
            output.extend([f"{item.quantity} {item.item_name}", "confirm"])
        return output


class BuyScreen(Screen):
    def __init__(
        self,
        *args,
        actions: typing.Iterable[ListItem] | None = None,
        stop_buy_event: asyncio.Event | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        assert actions is not None
        self.actions: typing.Iterable[ListItem] = actions
        if stop_buy_event is None:
            raise RuntimeError("stop_buy_event was not set!")
        self.stop_buy_event = stop_buy_event

    def compose(self) -> ComposeResult:
        yield ListView(*self.actions)


class ConfirmScreen(Screen):
    CSS = """
 ConfirmScreen {
     align: center middle;
 }

 #dialog {
     grid-size: 2;
     grid-gutter: 1 2;
     grid-rows: 1fr 3;
     padding: 0 1;
     width: 60;
     height: 11;
     border: thick $background 80%;
     background: $surface;
 }

 #question {
     column-span: 2;
     height: 1fr;
     width: 1fr;
     content-align: center middle;
 }

 Button {
     width: 100%;
 }
     """

    def __init__(self, *args, sell_total: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.sell_total = sell_total

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"Have you sold {self.sell_total}?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit(result=self.sell_total)
        else:
            self.app.pop_screen()


class SellTotal(Digits):
    sell_total = reactive(0)
    can_focus = False

    def watch_sell_total(self, sell_total: int) -> None:
        self.update(str(math.ceil(sell_total)))


class StoreTable(DataTable):
    BINDINGS = [
        ("+,add", "handle_item_count_change('increment')", "Add Item"),
        ("-,subtract", "handle_item_count_change('decrement')", "Remove Item"),
        ("S", "handle_sale_change('increment')", "Adds 10% Sale"),
        ("s", "handle_sale_change('decrement')", "Removes 10% Sale"),
        ("1", "handle_preset(1)", "preset 1"),
        ("2", "handle_preset(2)", "preset 2"),
        ("0", "handle_preset(None)", "Reset store"),
    ]
    sell_total = reactive(0)

    def __init__(
        self,
        *args,
        quota: int = 0,
        moon_amount: int = 0,
        version: str = "v73",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.quota = quota
        self.moon_amount = moon_amount
        self.version = version

    @property
    def headers(self) -> tuple[str, str, str, str, str]:
        # return "Quantity", "Sale Percentage", "Item", "Sale Price"
        return "Quantity", "Sale Percentage", "Item", "Sale Price", "Original Price"

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns(*self.headers)
        self.add_rows(get_store_data(self.version))

    def action_handle_preset(self, preset: int | None) -> None:
        self.clear()
        self.add_rows(get_store_data(self.version, preset))
        self.update_sell_total()

    @property
    def all_rows(self) -> list[StoreItem]:
        rows = []
        for values in self._data.values():
            rows.append(StoreItem(*values.values()))
        return rows

    @property
    def current_row(self) -> StoreItem:
        cursor = Coordinate(self.cursor_coordinate.row, 1)
        return StoreItem(*self.get_row_at(cursor.row))

    def update_sell_total(self) -> None:
        amounts: list[float | int] = [
            row.sale_price * row.quantity for row in self.all_rows
        ]
        app: Store = typing.cast(Store, self.app)
        # mypy is saying "expected Iterable[bool]" here and I can't be bothered to figure out way
        app.update_sell_total(
            calculate_overtime_sell(
                math.ceil(sum(amounts) + self.moon_amount), self.quota
            )
        )  # type: ignore

    def action_handle_item_count_change(
        self, change_type: typing.Literal["increment", "decrement"]
    ) -> None:
        row_data = self.current_row
        cursor: Coordinate = self.cursor_coordinate
        if change_type == "increment":
            self.update_cell_at(cursor, row_data.quantity + 1)
        else:
            self.update_cell_at(cursor, max(row_data.quantity - 1, 0))
        self.update_sell_total()

    def action_handle_sale_change(
        self, change_type: typing.Literal["increment", "decrement"]
    ) -> None:
        row_data = self.current_row
        sale_percentage_cursor = Coordinate(self.cursor_coordinate.row, 1)
        sale_amount_cursor = Coordinate(self.cursor_coordinate.row, 3)
        if change_type == "increment":
            new_sale_percentage = min(row_data.sale_percentage + 10, 80)
        else:
            new_sale_percentage = max(row_data.sale_percentage - 10, 0)
        new_sale_price = row_data.original_price * ((100 - new_sale_percentage) / 100)
        if new_sale_price.is_integer():
            new_sale_price = int(new_sale_price)
        self.update_cell_at(sale_percentage_cursor, new_sale_percentage)
        self.update_cell_at(sale_amount_cursor, new_sale_price)
        self.update_sell_total()


class Store(App):
    BINDINGS = [
        ("C", "handle_confirm()", "Confirm and exit"),
        ("D", "handle_do_sale()", "Do The Thing"),
        ("d", "handle_exit_sale_early()", "Exit the sale checklist"),
    ]
    sell_total = reactive(0)

    def __init__(
        self,
        *args,
        quota: int = 0,
        moon_amount: int = 0,
        version: str = "v73",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.quota: int = quota
        self.moon_amount: int = moon_amount
        self.version = version
        self.sell_total = calculate_overtime_sell(self.moon_amount, self.quota)
        self.stop_buy_event = asyncio.Event()

    @property
    def headers(self) -> tuple[str, str, str, str, str]:
        return "Quantity", "Sale Percentage", "Item", "Sale Price", "Original Price"

    def update_sell_total(self, sell_total: int) -> None:
        self.sell_total = sell_total

    def compose(self) -> ComposeResult:
        store_table = StoreTable(
            quota=self.quota, moon_amount=self.moon_amount, version=self.version
        )
        yield store_table
        yield SellTotal().data_bind(Store.sell_total)
        footer = Footer()
        footer.show_command_palette = False
        footer.compact = True
        yield footer

    def action_handle_confirm(self) -> None:
        self.push_screen(ConfirmScreen(sell_total=self.sell_total))

    @work(exclusive=True)
    async def manage_clipboard(self, store_table: StoreTable) -> None:
        cache_directory.mkdir(parents=True, exist_ok=True)
        pasted_dir = cache_directory / "pasted"
        pasted_file = pasted_dir / "pasted"
        pasted_file.parent.mkdir(parents=True, exist_ok=True)
        chunked_buys = construct_buy_command_list(store_table.all_rows)
        pasted_file.unlink(missing_ok=True)
        messages = [ListItem(Label("Starting buy"))]
        for chunk in chunked_buys:
            messages.extend(
                [ListItem(Label(command)) for command in chunk.sell_commands]
            )
            messages.append(
                ListItem(Label("Wait for dropship. Paste when ready for next."))
            )
        # get rid of the last wait.
        messages.pop()
        screen = BuyScreen(actions=messages, stop_buy_event=self.stop_buy_event)
        await self.push_screen(screen)
        with asyncinotify.Inotify() as inotify:
            inotify.add_watch(pasted_dir, asyncinotify.Mask.CREATE)
            list_view = screen.query_one(ListView)
            for index, chunk in enumerate(chunked_buys):
                for sell_command in chunk.sell_commands:
                    pyperclip.copy(sell_command)
                    list_view.action_cursor_down()
                    await self.wait_for_file(inotify)
                    pasted_file.unlink(missing_ok=True)
                    if self.stop_buy_event.is_set():
                        await self.app.pop_screen()
                        self.stop_buy_event.clear()
                        return
                if index + 1 == len(chunked_buys):
                    break
                pyperclip.copy("")
                list_view.action_cursor_down()
                await self.wait_for_file(inotify)
                pasted_file.unlink(missing_ok=True)
                if self.stop_buy_event.is_set():
                    await self.app.pop_screen()
                    self.stop_buy_event.clear()
                    return
            await self.app.pop_screen()
            pyperclip.copy("scan")

    def action_handle_do_sale(self) -> None:
        self.manage_clipboard(self.query_one(StoreTable))

    def action_handle_exit_sale_early(self) -> None:
        self.stop_buy_event.set()

    async def wait_for_file(self, watcher: asyncinotify.Inotify) -> None:
        self.stop_buy_event.clear()
        tasks = [self.stop_buy_event.wait(), watcher.get()]
        async for _ in asyncio.as_completed(tasks):
            print("Exiting")
            return


def get_script_dir() -> Path:
    return Path(__file__).resolve().parent


def get_store_data(version: str, preset: int | None = None) -> list[StoreItem]:
    script_dir = get_script_dir()
    store_price_file = script_dir / "data" / version / "store-prices.json"
    if preset is not None:
        store_price_file = script_dir / "data" / version / "presets" / f"{preset}.json"
    if not store_price_file.exists():
        raise FileNotFoundError(f"Store price file {store_price_file} not found")
    prices = json.loads(store_price_file.read_text())
    return [StoreItem(*item) for item in prices]


def construct_buy_command_list(buy_list: list[StoreItem]) -> list[StoreItemList]:
    naive_buy_list = list(
        sorted(
            filter(lambda x: x.quantity > 0, buy_list),
            key=lambda x: x.quantity,
            reverse=True,
        )
    )
    buy_list = []
    for item in naive_buy_list:
        # This is _not_ a protected member, idiot.
        # noinspection PyProtectedMember
        item_dict = item._asdict()
        # Items with a decimal point should be purchased one at a time so that the value gets rounded down
        if isinstance(item.sale_price, float):
            item_dict["quantity"] = 1
            for _ in range(item.quantity):
                buy_list.append(StoreItem(**item_dict))
        # If purchasing more than 10 items, you need to split it up and buy the remaining items separately
        elif item.quantity > 10:
            remaining_quantity = item.quantity
            while remaining_quantity > 10:
                item_dict["quantity"] = 10
                buy_list.append(StoreItem(**item_dict))
                remaining_quantity -= 10
            item_dict["quantity"] = remaining_quantity
            buy_list.append(StoreItem(**item_dict))
        else:
            buy_list.append(item)
    buy_list.sort(key=lambda x: x.quantity, reverse=True)
    # time for binpacking
    item_bins: list[StoreItemList] = []
    cruiser: StoreItem | None = None
    for item in buy_list:
        # Cruiser should always be in its own bin.
        if item.item_name == "Cruiser":
            cruiser = item
            continue
        for item_bin in item_bins:
            if len(item_bin) + item.quantity <= StoreItemList.max_length:
                item_bin.append(item)
                break
        else:
            item_bin = StoreItemList([item])
            item_bins.append(item_bin)
    if cruiser:
        item_bins.append(StoreItemList([cruiser]))
    return item_bins


def run(quota: int, moon_amount: int, version: str) -> int | None:
    store = Store(quota=quota, moon_amount=moon_amount, version=version)
    result = store.run()
    return result


def calculate_overtime_sell(wanted_credits: int, quota_amount: int) -> int:
    if quota_amount < wanted_credits - 75:
        return math.floor(((5 * wanted_credits) + 75 + quota_amount + 5) / 6)
    return max(wanted_credits, quota_amount)


def calculate_early_sell(quota_days_played: int, quota_amount: int) -> int:
    assert 0 <= quota_days_played <= 3
    match quota_days_played:
        case 0:
            # TODO double check this
            sell_divisor = 30.333333
        case 1:
            sell_divisor = 53.333333
        case 2:
            sell_divisor = 76.666666
        case 3:
            sell_divisor = 100

    return math.ceil((quota_amount * 100) / sell_divisor)

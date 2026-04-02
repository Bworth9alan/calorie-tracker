import streamlit as st
import json
import os
from datetime import date, datetime
import pandas as pd
import matplotlib.pyplot as plt
import calendar


DATA_FILE = "calorie_tracker_data.json"

# Eggs are the only count-based food.
# Everything else is handled in ounces.
DEFAULT_FOODS = {
    "Steak": {"unit": "oz", "protein": 7.0, "fat": 5.0, "calories": 75.0},
    "Ground Beef": {"unit": "oz", "protein": 7.0, "fat": 6.0, "calories": 80.0},
    "Chicken Breast": {"unit": "oz", "protein": 8.0, "fat": 1.0, "calories": 45.0},
    "Salmon": {"unit": "oz", "protein": 6.0, "fat": 4.0, "calories": 60.0},
    "Turkey": {"unit": "oz", "protein": 8.0, "fat": 1.0, "calories": 45.0},
    "Tuna": {"unit": "oz", "protein": 7.0, "fat": 0.5, "calories": 35.0},
    "Oysters": {"unit": "oz", "protein": 2.0, "fat": 0.5, "calories": 20.0},
    "Eggs": {"unit": "egg", "protein": 6.0, "fat": 5.0, "calories": 70.0},
    "Bacon": {"unit": "oz", "protein": 8.0, "fat": 12.0, "calories": 150.0},
    "Butter": {"unit": "oz", "protein": 0.0, "fat": 23.0, "calories": 204.0},
    "Cheese": {"unit": "oz", "protein": 7.0, "fat": 9.0, "calories": 110.0},
    "Milk": {"unit": "oz", "protein": 1.0, "fat": 1.0, "calories": 19.0},
    "Cottage Cheese": {"unit": "oz", "protein": 3.1, "fat": 0.6, "calories": 28.0},
    "Plain Yogurt": {"unit": "oz", "protein": 2.8, "fat": 1.4, "calories": 42.0},
    "Protein Drink": {"unit": "oz", "protein": 1.9, "fat": 0.2, "calories": 10.0},
    "Rice": {"unit": "oz", "protein": 0.7, "fat": 0.1, "calories": 37.0},
    "Bread": {"unit": "oz", "protein": 2.6, "fat": 1.0, "calories": 75.0},
    "Dates": {"unit": "oz", "protein": 0.7, "fat": 0.0, "calories": 79.0},
    "Almond Butter": {"unit": "oz", "protein": 6.0, "fat": 16.0, "calories": 170.0},
    "Avocado": {"unit": "oz", "protein": 0.6, "fat": 4.3, "calories": 45.0},
}


def is_eggs(food_name: str) -> bool:
    return food_name.strip().lower() == "eggs"


def normalize_food_unit(food_name: str, food_data: dict) -> dict:
    """
    Force everything to ounces except Eggs.
    This keeps older saved data from showing random units.
    """
    normalized = food_data.copy()
    normalized["unit"] = "egg" if is_eggs(food_name) else "oz"
    return normalized


def load_data():
    data = {}

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if not isinstance(data, dict):
        data = {}

    if "goal_weight" not in data:
        old_goal = data.get("goal", 0.0)
        data["goal_weight"] = float(old_goal) if old_goal not in ("", None) else 0.0

    if "foods" not in data or not isinstance(data["foods"], dict):
        data["foods"] = {}

    if "logs" not in data or not isinstance(data["logs"], dict):
        data["logs"] = {}

    if "weights" not in data or not isinstance(data["weights"], dict):
        data["weights"] = {}

    if "fasts" not in data or not isinstance(data["fasts"], list):
        data["fasts"] = []

    # Add defaults if missing
    for food_name, values in DEFAULT_FOODS.items():
        if food_name not in data["foods"]:
            data["foods"][food_name] = values.copy()
        else:
            existing = data["foods"][food_name]
            for key, val in values.items():
                if key not in existing:
                    existing[key] = val

    # Normalize all food units:
    # eggs = egg, everything else = oz
    normalized_foods = {}
    for food_name, food_data in data["foods"].items():
        normalized_foods[food_name] = normalize_food_unit(food_name, food_data)
    data["foods"] = normalized_foods

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_day_entries(data, day_str):
    return data["logs"].get(day_str, [])


def set_day_entries(data, day_str, entries):
    data["logs"][day_str] = entries


def calculate_day_totals(data, day_str):
    entries = get_day_entries(data, day_str)
    total_protein = 0.0
    total_fat = 0.0
    total_calories = 0.0

    for entry in entries:
        food_name = entry["food"]
        amount = float(entry["amount"])

        if food_name in data["foods"]:
            food = data["foods"][food_name]
            total_protein += float(food["protein"]) * amount
            total_fat += float(food["fat"]) * amount
            total_calories += float(food["calories"]) * amount

    return total_protein, total_fat, total_calories


def get_food_breakdown(data, entry):
    food_name = entry["food"]
    amount = float(entry["amount"])
    food = data["foods"][food_name]

    return {
        "food": food_name,
        "unit": food["unit"],
        "amount": amount,
        "protein": float(food["protein"]) * amount,
        "fat": float(food["fat"]) * amount,
        "calories": float(food["calories"]) * amount,
    }


def get_day_color(total_calories, daily_limit):
    if total_calories <= 0 or daily_limit <= 0:
        return "⬛"

    ratio = total_calories / daily_limit
    if ratio <= 0.75:
        return "🟢"
    elif ratio <= 1.0:
        return "🟡"
    else:
        return "🔴"


def build_month_grid(year, month):
    cal = calendar.Calendar(firstweekday=6)
    return cal.monthdayscalendar(year, month)


def get_weight_for_day(data, day_str):
    return data["weights"].get(day_str, {"morning": "", "evening": ""})


def save_weight_for_day(data, day_str, morning, evening):
    data["weights"][day_str] = {
        "morning": morning,
        "evening": evening,
    }


def build_weight_dataframe(data):
    rows = []

    for day_str, values in data["weights"].items():
        rows.append(
            {
                "date": pd.to_datetime(day_str),
                "morning": pd.to_numeric(values.get("morning", ""), errors="coerce"),
                "evening": pd.to_numeric(values.get("evening", ""), errors="coerce"),
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("date")


def build_calorie_dataframe(data):
    rows = []

    for day_str in sorted(data["logs"].keys()):
        _, _, total_calories = calculate_day_totals(data, day_str)
        rows.append(
            {
                "date": pd.to_datetime(day_str),
                "calories": total_calories,
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("date")


def get_active_fast(data):
    for fast in reversed(data["fasts"]):
        if not fast.get("end"):
            return fast
    return None


def start_fast(data):
    if get_active_fast(data) is None:
        data["fasts"].append(
            {
                "start": datetime.now().isoformat(),
                "end": None,
                "hours": None,
                "duration_display": None,
            }
        )


def end_fast(data):
    active = get_active_fast(data)
    if active is not None:
        end_time = datetime.now()
        start_time = datetime.fromisoformat(active["start"])
        delta = end_time - start_time
        hours = round(delta.total_seconds() / 3600, 2)

        active["end"] = end_time.isoformat()
        active["hours"] = hours
        active["duration_display"] = format_timedelta(delta)
        return hours, format_timedelta(delta)

    return None, None


def format_timedelta(delta):
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder = remainder % 3600
    minutes = remainder // 60
    seconds = remainder % 60

    return f"{days}d {hours:02}h {minutes:02}m {seconds:02}s"


def get_current_fast_display(data):
    active_fast = get_active_fast(data)
    if not active_fast:
        return None

    start_time = datetime.fromisoformat(active_fast["start"])
    now_time = datetime.now()
    return format_timedelta(now_time - start_time)


def build_day_food_dataframe(data, day_str):
    entries = get_day_entries(data, day_str)
    rows = []

    for entry in entries:
        breakdown = get_food_breakdown(data, entry)
        rows.append(
            {
                "Food": breakdown["food"],
                "Amount": breakdown["amount"],
                "Unit": breakdown["unit"],
                "Protein (g)": round(breakdown["protein"], 1),
                "Fat (g)": round(breakdown["fat"], 1),
                "Calories": round(breakdown["calories"], 1),
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


st.set_page_config(page_title="Calorie Tracker Webpage", layout="wide")

data = load_data()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = str(date.today())

if "food_entry_date" not in st.session_state:
    st.session_state.food_entry_date = date.today()


@st.dialog("Food Day Details", width="large")
def open_food_day_dialog(day_str):
    st.subheader(f"Food Summary for {day_str}")

    entries = get_day_entries(data, day_str)
    total_protein, total_fat, total_calories = calculate_day_totals(data, day_str)
    day_color = get_day_color(total_calories, daily_limit)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Calories", f"{total_calories:.1f}")
    with c2:
        st.metric("Protein", f"{total_protein:.1f} g")
    with c3:
        st.metric("Fat", f"{total_fat:.1f} g")
    with c4:
        st.metric("Status", day_color)

    if daily_limit > 0:
        st.write(f"Calories Left: **{daily_limit - total_calories:.1f}**")

    if not entries:
        st.write("No foods logged for this day.")
        return

    st.write("Foods Eaten:")

    food_names = sorted(list(data["foods"].keys()))
    updated_entries = []
    delete_indexes = set()

    for i, entry in enumerate(entries):
        st.markdown("---")
        row1, row2, row3 = st.columns([3, 2, 1])

        with row1:
            current_food = st.selectbox(
                f"Food {i+1}",
                food_names,
                index=food_names.index(entry["food"]) if entry["food"] in food_names else 0,
                key=f"dialog_food_{day_str}_{i}",
            )

        chosen_food = data["foods"][current_food]
        amount_label = "How many eggs?" if chosen_food["unit"] == "egg" else "How many ounces?"

        with row2:
            amount = st.number_input(
                f"{amount_label} ({i+1})",
                min_value=0.0,
                value=float(entry["amount"]),
                step=1.0,
                key=f"dialog_amount_{day_str}_{i}",
            )

        with row3:
            delete_this = st.checkbox("Delete", key=f"dialog_delete_{day_str}_{i}")

        updated_entries.append({"food": current_food, "amount": amount})

        st.write(
            f"Unit: **{chosen_food['unit']}** | "
            f"Protein: **{float(chosen_food['protein']) * amount:.1f} g** | "
            f"Fat: **{float(chosen_food['fat']) * amount:.1f} g** | "
            f"Calories: **{float(chosen_food['calories']) * amount:.1f}**"
        )

        if delete_this:
            delete_indexes.add(i)

    if st.button("Save Changes To This Day"):
        final_entries = [
            item for idx, item in enumerate(updated_entries) if idx not in delete_indexes
        ]
        set_day_entries(data, day_str, final_entries)
        save_data(data)
        st.success("Day updated.")
        st.rerun()


@st.dialog("Weight Day Details", width="medium")
def open_weight_day_dialog(day_str):
    st.subheader(f"Weight for {day_str}")

    weight_values = get_weight_for_day(data, day_str)

    morning = st.text_input(
        "Morning Weight",
        value=str(weight_values.get("morning", "")),
        key=f"dialog_morning_{day_str}",
    )
    evening = st.text_input(
        "Evening Weight",
        value=str(weight_values.get("evening", "")),
        key=f"dialog_evening_{day_str}",
    )

    if st.button("Save Weight Changes"):
        save_weight_for_day(data, day_str, morning, evening)
        save_data(data)
        st.success("Weight saved.")
        st.rerun()


st.title("Calorie Tracker Webpage")

goal_weight = st.number_input(
    "Goal Weight (lbs)",
    min_value=0.0,
    value=float(data.get("goal_weight", 0.0)),
    step=1.0,
)
data["goal_weight"] = goal_weight
save_data(data)

daily_limit = goal_weight * 12
daily_protein_target = goal_weight * 1

st.subheader("Total Daily Calories")

g1, g2, g3 = st.columns(3)
with g1:
    st.metric("Total Daily Calories", f"{daily_limit:.0f}")
with g2:
    st.metric("Daily Protein Target", f"{daily_protein_target:.0f} g")
with g3:
    st.metric("Protein Calories", f"{daily_protein_target * 4:.0f}")

st.divider()

st.subheader("Fast Tracker")

active_fast = get_active_fast(data)

fast_col1, fast_col2, fast_col3 = st.columns([1, 1, 2])

with fast_col1:
    if st.button("Start Fast", use_container_width=True):
        if active_fast is None:
            start_fast(data)
            save_data(data)
            st.rerun()

with fast_col2:
    if st.button("End Fast", use_container_width=True):
        hours, duration_display = end_fast(data)
        save_data(data)
        if hours is not None:
            st.success(f"Fast ended. Total time: {duration_display}")
        st.rerun()

with fast_col3:
    # Live-ish display area. The page needs to rerun to visibly update.
    # On Streamlit Community Cloud / many setups, this can update when the page reruns.
    # If st.fragment is available in your version, this will auto-refresh every second.
    try:
        @st.fragment(run_every=1)
        def fast_timer_fragment():
            current_active_fast = get_active_fast(data)
            if current_active_fast:
                st.info(f"Current Fast: {get_current_fast_display(data)}")
            else:
                if data["fasts"]:
                    last_fast = data["fasts"][-1]
                    if last_fast.get("duration_display"):
                        st.info(f"Last Fast: {last_fast['duration_display']}")
                    elif last_fast.get("hours") is not None:
                        st.info(f"Last Fast: {last_fast['hours']} hours")
                    else:
                        st.info("No active fast")
                else:
                    st.info("No fast logged yet")

        fast_timer_fragment()
    except Exception:
        # Fallback if fragment isn't supported
        if active_fast:
            st.info(f"Current Fast: {get_current_fast_display(data)}")
        else:
            if data["fasts"]:
                last_fast = data["fasts"][-1]
                if last_fast.get("duration_display"):
                    st.info(f"Last Fast: {last_fast['duration_display']}")
                elif last_fast.get("hours") is not None:
                    st.info(f"Last Fast: {last_fast['hours']} hours")
                else:
                    st.info("No active fast")
            else:
                st.info("No fast logged yet")

st.divider()

selected_day = st.session_state.selected_day

st.subheader("Daily Weight")

weight_values = get_weight_for_day(data, selected_day)

w1, w2, w3 = st.columns(3)
with w1:
    morning_weight = st.text_input(
        "Morning Weight",
        value=str(weight_values.get("morning", "")),
        key=f"morning_main_{selected_day}",
    )
with w2:
    evening_weight = st.text_input(
        "Evening Weight",
        value=str(weight_values.get("evening", "")),
        key=f"evening_main_{selected_day}",
    )
with w3:
    st.write("")
    st.write("")
    if st.button("Save Weight For Selected Day"):
        save_weight_for_day(data, selected_day, morning_weight, evening_weight)
        save_data(data)
        st.success("Weight saved.")
        st.rerun()

st.divider()

st.subheader("Food List")

food_names = sorted(list(data["foods"].keys()))
selected_food = st.selectbox("Choose Food", food_names)
food = data["foods"][selected_food]

left, right = st.columns([1, 1])

with left:
    st.write(f"Unit: **{food['unit']}**")
    st.write(f"Protein per {food['unit']}: **{food['protein']} g**")
    st.write(f"Fat per {food['unit']}: **{food['fat']} g**")
    st.write(f"Calories per {food['unit']}: **{food['calories']}**")

with right:
    edit_food = st.toggle("Edit Selected Food")
    if edit_food:
        st.write("Everything stays in ounces except Eggs.")

        edit_protein = st.number_input(
            "Protein per unit",
            min_value=0.0,
            value=float(food["protein"]),
            step=0.1,
            key=f"edit_protein_{selected_food}",
        )
        edit_fat = st.number_input(
            "Fat per unit",
            min_value=0.0,
            value=float(food["fat"]),
            step=0.1,
            key=f"edit_fat_{selected_food}",
        )
        edit_calories = st.number_input(
            "Calories per unit",
            min_value=0.0,
            value=float(food["calories"]),
            step=1.0,
            key=f"edit_calories_{selected_food}",
        )

        if st.button("Save Food Edit"):
            data["foods"][selected_food] = {
                "unit": "egg" if is_eggs(selected_food) else "oz",
                "protein": edit_protein,
                "fat": edit_fat,
                "calories": edit_calories,
            }
            save_data(data)
            st.success(f"{selected_food} updated.")
            st.rerun()

st.markdown("### Add Food To Selected Day")

entry_date = st.date_input(
    "Choose date for food entry",
    value=st.session_state.food_entry_date,
    key="food_entry_date_picker",
)
st.session_state.food_entry_date = entry_date
food_entry_day_str = str(entry_date)

if selected_food == "Eggs":
    amount_label = "How many eggs did you have?"
else:
    amount_label = "How many ounces did you have?"

add_amount = st.number_input(
    amount_label,
    min_value=0.0,
    step=1.0,
    key=f"amount_{selected_food}_{food_entry_day_str}",
)

calc_protein = float(food["protein"]) * add_amount
calc_fat = float(food["fat"]) * add_amount
calc_calories = float(food["calories"]) * add_amount

st.write(f"Adding to: **{food_entry_day_str}**")
st.write(f"Protein: **{calc_protein:.1f} g**")
st.write(f"Fat: **{calc_fat:.1f} g**")
st.write(f"Calories: **{calc_calories:.1f}**")

add_col1, add_col2 = st.columns(2)

with add_col1:
    if st.button("Add Selected Food", use_container_width=True):
        if add_amount <= 0:
            st.error("Enter an amount greater than 0.")
        else:
            data["logs"].setdefault(food_entry_day_str, []).append(
                {"food": selected_food, "amount": add_amount}
            )
            save_data(data)
            st.session_state.selected_day = food_entry_day_str
            st.success(f"Added {selected_food} to {food_entry_day_str}.")
            st.rerun()

with add_col2:
    if st.button("Set Selected Day To This Date", use_container_width=True):
        st.session_state.selected_day = food_entry_day_str
        st.success(f"Selected day changed to {food_entry_day_str}.")
        st.rerun()

selected_day_df = build_day_food_dataframe(data, food_entry_day_str)
if not selected_day_df.empty:
    st.markdown(f"#### Foods already saved for {food_entry_day_str}")
    st.dataframe(selected_day_df, use_container_width=True)
else:
    st.write(f"No foods saved yet for {food_entry_day_str}.")

st.divider()

st.subheader("Add New Food")

with st.expander("Open Add New Food"):
    new_food_name = st.text_input("Food Name")

    st.write("Everything new will be saved in ounces except Eggs.")

    new_food_protein = st.number_input(
        "Protein per unit",
        min_value=0.0,
        step=0.1,
        key="new_food_protein",
    )
    new_food_fat = st.number_input(
        "Fat per unit",
        min_value=0.0,
        step=0.1,
        key="new_food_fat",
    )
    new_food_calories = st.number_input(
        "Calories per unit",
        min_value=0.0,
        step=1.0,
        key="new_food_calories",
    )

    if st.button("Save New Food"):
        clean_name = new_food_name.strip()

        if not clean_name:
            st.error("Enter a food name.")
        else:
            data["foods"][clean_name] = {
                "unit": "egg" if is_eggs(clean_name) else "oz",
                "protein": new_food_protein,
                "fat": new_food_fat,
                "calories": new_food_calories,
            }
            save_data(data)
            st.success(f"{clean_name} saved.")
            st.rerun()

st.divider()

today_dt = date.today()

month_col1, month_col2 = st.columns(2)
with month_col1:
    month_choice = st.selectbox(
        "Month",
        list(range(1, 13)),
        index=today_dt.month - 1,
        format_func=lambda m: calendar.month_name[m],
    )
with month_col2:
    year_choice = st.selectbox(
        "Year",
        list(range(today_dt.year - 2, today_dt.year + 3)),
        index=2,
    )

month_grid = build_month_grid(year_choice, month_choice)
weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

st.subheader("Food Calendar")

header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    header_cols[i].markdown(f"**{day_name}**")

for week in month_grid:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.write("")
            else:
                day_str = str(date(year_choice, month_choice, day_num))
                _, _, total_calories = calculate_day_totals(data, day_str)
                color = get_day_color(total_calories, daily_limit)

                if st.button(
                    f"{color} {day_num}",
                    key=f"food_day_{day_str}",
                    use_container_width=True,
                ):
                    st.session_state.selected_day = day_str
                    st.session_state.food_entry_date = date.fromisoformat(day_str)
                    open_food_day_dialog(day_str)

st.write(f"**Selected Food Day:** {st.session_state.selected_day}")

selected_food_day_df = build_day_food_dataframe(data, st.session_state.selected_day)
if not selected_food_day_df.empty:
    st.markdown(f"### Foods for {st.session_state.selected_day}")
    st.dataframe(selected_food_day_df, use_container_width=True)
else:
    st.write(f"No foods logged yet for {st.session_state.selected_day}.")

st.subheader("Weight Calendar")

weight_header_cols = st.columns(7)
for i, day_name in enumerate(weekdays):
    weight_header_cols[i].markdown(f"**{day_name}**")

for week in month_grid:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.write("")
            else:
                day_str = str(date(year_choice, month_choice, day_num))
                if st.button(
                    f"{day_num}",
                    key=f"weight_day_{day_str}",
                    use_container_width=True,
                ):
                    st.session_state.selected_day = day_str
                    open_weight_day_dialog(day_str)

st.write(f"**Selected Weight Day:** {st.session_state.selected_day}")

st.divider()

graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    show_weight_graph = st.toggle("Show Weight Graph")

    if show_weight_graph:
        st.subheader("Weight Graph")
        weight_df = build_weight_dataframe(data)

        if weight_df.empty:
            st.write("No weight data yet.")
        else:
            weekly_df = weight_df[
                weight_df["date"] >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=7))
            ]

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                weekly_df["date"],
                weekly_df["morning"],
                marker="o",
                label="Morning Weight",
            )
            ax.plot(
                weekly_df["date"],
                weekly_df["evening"],
                marker="o",
                label="Evening Weight",
            )
            ax.set_xlabel("Date")
            ax.set_ylabel("Weight (lbs)")
            ax.set_title("Weight - Last 7 Days")
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)

            if st.toggle("Show Full Weight Table"):
                st.dataframe(
                    weight_df.assign(date=weight_df["date"].dt.strftime("%Y-%m-%d")),
                    use_container_width=True,
                )

with graph_col2:
    show_calorie_graph = st.toggle("Show Calorie Graph")

    if show_calorie_graph:
        st.subheader("Calorie Graph")
        cal_df = build_calorie_dataframe(data)

        if cal_df.empty:
            st.write("No calorie data yet.")
        else:
            weekly_cal_df = cal_df[
                cal_df["date"] >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=7))
            ]

            fig, ax = plt.subplots(figsize=(10, 4))

            under_df = weekly_cal_df[weekly_cal_df["calories"] <= daily_limit]
            over_df = weekly_cal_df[weekly_cal_df["calories"] > daily_limit]

            if not under_df.empty:
                ax.plot(
                    under_df["date"],
                    under_df["calories"],
                    marker="o",
                    color="green",
                    label="Under",
                )

            if not over_df.empty:
                ax.plot(
                    over_df["date"],
                    over_df["calories"],
                    marker="o",
                    color="red",
                    label="Over",
                )

            if daily_limit > 0:
                ax.axhline(
                    y=daily_limit,
                    linestyle="--",
                    color="black",
                    label="Daily Limit",
                )

            ax.set_xlabel("Date")
            ax.set_ylabel("Calories")
            ax.set_title("Calories - Last 7 Days")
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)

            if st.toggle("Show Full Calorie Table"):
                st.dataframe(
                    cal_df.assign(date=cal_df["date"].dt.strftime("%Y-%m-%d")),
                    use_container_width=True,
                )

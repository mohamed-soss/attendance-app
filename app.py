import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import base64
import plotly.express as px
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

# Egypt timezone
EGYPT_TZ = ZoneInfo("Africa/Cairo")

# File to store data
DATA_FILE = 'attendance_data.csv'
BACKUP_EXCEL = 'attendance_backup.xlsx'

# Define expected columns
EXPECTED_COLUMNS = ['User', 'Date', 'CheckIn', 'CheckOut', 
                    'Break1Start', 'Break1End', 'Break2Start', 'Break2End', 
                    'Break3Start', 'Break3End', 'TotalHours', 'BreakDuration', 'Active']

# Time-related columns to enforce string dtype
TIME_COLUMNS = ['CheckIn', 'CheckOut', 'Break1Start', 'Break1End', 
                'Break2Start', 'Break2End', 'Break3Start', 'Break3End']

# Load data and ensure all columns exist with correct dtypes
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            if col == 'Active':
                df[col] = True
            elif col in TIME_COLUMNS:
                df[col] = pd.NA
            else:
                df[col] = pd.NA
    # Convert time columns to string to match TextColumn
    for col in TIME_COLUMNS:
        df[col] = df[col].astype("string").fillna(pd.NA)
else:
    # Initialize with string dtype for time columns
    dtypes = {col: "string" for col in TIME_COLUMNS}
    dtypes.update({'User': 'string', 'Date': 'string', 'TotalHours': 'float64', 
                   'BreakDuration': 'float64', 'Active': 'boolean'})
    df = pd.DataFrame(columns=EXPECTED_COLUMNS).astype(dtypes)

# Function to save data to CSV and Excel
def save_data():
    global df
    df.to_csv(DATA_FILE, index=False)
    with pd.ExcelWriter(BACKUP_EXCEL, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='DataMatrix')

# Function to restore data from Excel
def restore_from_excel(uploaded_file):
    global df
    try:
        uploaded_df = pd.read_excel(uploaded_file, sheet_name='DataMatrix')
        # Validate columns
        if not all(col in uploaded_df.columns for col in ['User', 'Date']):
            st.error("Uploaded Excel file must contain 'User' and 'Date' columns.")
            return False
        # Ensure all expected columns are present
        for col in EXPECTED_COLUMNS:
            if col not in uploaded_df.columns:
                if col == 'Active':
                    uploaded_df[col] = True
                elif col in TIME_COLUMNS:
                    uploaded_df[col] = pd.NA
                else:
                    uploaded_df[col] = pd.NA
        # Convert time columns to string
        for col in TIME_COLUMNS:
            uploaded_df[col] = uploaded_df[col].astype("string").fillna(pd.NA)
        # Ensure other columns have correct dtypes
        uploaded_df['User'] = uploaded_df['User'].astype("string")
        uploaded_df['Date'] = uploaded_df['Date'].astype("string")
        uploaded_df['TotalHours'] = uploaded_df['TotalHours'].astype("float64")
        uploaded_df['BreakDuration'] = uploaded_df['BreakDuration'].astype("float64")
        uploaded_df['Active'] = uploaded_df['Active'].astype("boolean")
        # Merge with existing data, prioritizing uploaded data for duplicates
        df = pd.concat([df, uploaded_df]).drop_duplicates(subset=['User', 'Date', 'CheckIn'], keep='last').reset_index(drop=True)
        save_data()
        return True
    except Exception as e:
        st.error(f"Error restoring data: {str(e)}")
        return False

# Function to calculate shift date (shift starts at 4 PM, ends at 12 AM next day, but date is the start day)
def get_shift_date():
    now = datetime.now(EGYPT_TZ)
    if now.hour < 4 or (now.hour == 4 and now.minute == 0):
        return (now - timedelta(days=1)).date()
    else:
        return now.date()

# Function to format time as 12-hour string (e.g., "12:45 AM")
def format_time(dt):
    if isinstance(dt, datetime):
        return dt.strftime("%I:%M %p").lstrip("0")
    return dt

# Function to parse time string with shift date for calculations
def parse_time(time_str, shift_date):
    if pd.isna(time_str) or not isinstance(time_str, str):
        return None
    try:
        dt = datetime.strptime(f"{shift_date} {time_str}", "%Y-%m-%d %I:%M %p")
        dt = dt.replace(tzinfo=EGYPT_TZ)
        if dt.hour < 16 and time_str.endswith("AM"):
            dt += timedelta(days=1)
        return dt
    except ValueError:
        return None

# Function to calculate total hours and break duration
def calculate_times(row, shift_date):
    check_in = parse_time(row['CheckIn'], shift_date) if pd.notna(row['CheckIn']) else None
    check_out = parse_time(row['CheckOut'], shift_date) if pd.notna(row['CheckOut']) else None
    if check_in and check_out:
        total_hours = (check_out - check_in).total_seconds() / 3600
    else:
        total_hours = 0

    break_duration = 0
    for i in range(1, 4):
        start_col = f'Break{i}Start'
        end_col = f'Break{i}End'
        break_start = parse_time(row[start_col], shift_date) if pd.notna(row[start_col]) else None
        break_end = parse_time(row[end_col], shift_date) if pd.notna(row[end_col]) else None
        if break_start and break_end:
            break_duration += (break_end - break_start).total_seconds() / 3600

    return total_hours, break_duration

# Custom CSS for extreme modern GUI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

    body, .stApp {
        background: linear-gradient(45deg, #0f0c29, #302b63, #24243e);
        background-size: 200% 200%;
        animation: gradientShift 15s ease infinite;
        color: #ffffff;
        font-family: 'Orbitron', sans-serif;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .css-1lcbmhc {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        margin: 10px;
    }
    .nav-link {
        color: #00ffea !important;
        font-size: 18px;
        padding: 12px;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .nav-link:hover {
        background: rgba(0, 255, 234, 0.2) !important;
        transform: translateX(5px);
    }
    .nav-link-selected {
        background: linear-gradient(45deg, #00ffea, #ff00ff) !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px #00ffea;
    }

    h1, h2, h3 {
        color: #00ffea;
        font-weight: 700;
        text-shadow: 0 0 10px #00ffea, 0 0 20px #ff00ff;
        animation: glow 2s ease-in-out infinite alternate;
    }

    @keyframes glow {
        from { text-shadow: 0 0 5px #00ffea, 0 0 10px #ff00ff; }
        to { text-shadow: 0 0 10px #00ffea, 0 0 20px #ff00ff; }
    }

    .card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 0 15px rgba(0, 255, 234, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        animation: slideIn 0.5s ease-out;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 20px rgba(0, 255, 234, 0.5);
    }

    .stButton > button {
        background: linear-gradient(45deg, #00ffea, #ff00ff);
        color: #ffffff;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 700;
        border-radius: 10px;
        box-shadow: 0 0 10px #00ffea;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #ff00ff;
    }
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        transition: width 0.6s ease, height 0.6s ease;
    }
    .stButton > button:hover::after {
        width: 200px;
        height: 200px;
    }

    .stTextInput > div > div > input, .stSelectbox > div > select {
        background: rgba(255, 255, 255, 0.05);
        color: #ffffff;
        border: 1px solid #00ffea;
        border-radius: 10px;
        padding: 12px;
        font-size: 16px;
        box-shadow: 0 0 5px rgba(0, 255, 234, 0.3);
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > select:focus {
        border-color: #ff00ff;
        box-shadow: 0 0 10px #ff00ff;
    }

    .dataframe {
        background: rgba(255, 255, 255, 0.05);
        color: #ffffff;
        border-radius: 10px;
        border: 1px solid rgba(0, 255, 234, 0.3);
    }

    @keyframes slideIn {
        from { transform: translateX(-30px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    .stMarkdown, .stButton, .stTextInput, .stSelectbox {
        animation: slideIn 0.7s ease-out;
    }

    .stAlert {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid #00ffea;
        border-radius: 10px;
        color: #ffffff;
        box-shadow: 0 0 10px rgba(0, 255, 234, 0.3);
    }

    .stFormSubmitButton > button {
        background: linear-gradient(45deg, #00ffea, #ff00ff);
        color: #ffffff;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 700;
        border-radius: 10px;
        box-shadow: 0 0 10px #00ffea;
        margin-top: 10px;
        transition: all 0.3s ease;
    }
    .stFormSubmitButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #ff00ff;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for user selection
if 'selected_user' not in st.session_state:
    st.session_state.selected_user = None

# Sidebar for navigation
with st.sidebar:
    selected = option_menu(
        menu_title="Control Hub",
        options=["User Portal", "Admin Dashboard"],
        icons=["bi-person-circle", "bi-gear-fill"],
        menu_icon="bi-lightning-charge-fill",
        default_index=0,
        styles={
            "container": {"padding": "10px", "background": "transparent"},
            "icon": {"color": "#00ffea", "font-size": "24px"},
            "nav-link": {"font-size": "18px", "margin": "5px", "padding": "12px", "--hover-color": "rgba(0, 255, 234, 0.2)"},
            "nav-link-selected": {"background": "linear-gradient(45deg, #00ffea, #ff00ff)"},
        }
    )

if selected == "User Portal":
    st.title("Quantum Attendance")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # Get list of active users
        active_users = sorted(df[df['Active'] == True]['User'].unique().tolist())
        
        with st.form(key="user_selection_form"):
            if not active_users:
                st.warning("No active users available. Please contact the admin to add users.")
                user_name = None
            else:
                user_name = st.selectbox("Select your identity", options=active_users, placeholder="Choose User...", key="user_select")
                submitted = st.form_submit_button("Enter")  # Visible button labeled "Enter"
                if submitted:
                    if user_name:
                        st.session_state.selected_user = user_name
                    else:
                        st.error("Please select a user before submitting.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Use session state to display user session
    if st.session_state.selected_user:
        user_name = st.session_state.selected_user
        # Check if user is active
        user_records = df[df['User'] == user_name]
        user_active = user_records['Active'].any() if not user_records.empty else True
        if not user_active:
            st.error("Access Denied: User account has been deleted.")
            st.session_state.selected_user = None  # Reset selection
        else:
            shift_date = get_shift_date()
            user_rows = df[(df['User'] == user_name) & (df['Date'] == str(shift_date))]

            # Create a new record for each check-in
            if st.button("Start New Session", key="start_session"):
                new_row = {
                    'User': user_name,
                    'Date': str(shift_date),
                    'Active': True,
                    'CheckIn': pd.NA,
                    'CheckOut': pd.NA,
                    'Break1Start': pd.NA,
                    'Break1End': pd.NA,
                    'Break2Start': pd.NA,
                    'Break2End': pd.NA,
                    'Break3Start': pd.NA,
                    'Break3End': pd.NA,
                    'TotalHours': 0.0,
                    'BreakDuration': 0.0
                }
                new_row_df = pd.DataFrame([new_row]).astype({
                    'User': 'string',
                    'Date': 'string',
                    'CheckIn': 'string',
                    'CheckOut': 'string',
                    'Break1Start': 'string',
                    'Break1End': 'string',
                    'Break2Start': 'string',
                    'Break2End': 'string',
                    'Break3Start': 'string',
                    'Break3End': 'string',
                    'TotalHours': 'float64',
                    'BreakDuration': 'float64',
                    'Active': 'boolean'
                })
                df = pd.concat([df, new_row_df], ignore_index=True)
                save_data()
                st.success("New Session Initialized")
                user_rows = df[(df['User'] == user_name) & (df['Date'] == str(shift_date))]

            if not user_rows.empty:
                row_index = user_rows.index[-1]  # Most recent record
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns(2, gap="medium")

                with col1:
                    if st.button("Check In", key=f"check_in_{row_index}") and pd.isna(df.at[row_index, 'CheckIn']):
                        df.at[row_index, 'CheckIn'] = format_time(datetime.now(EGYPT_TZ))
                        total_hours, break_duration = calculate_times(df.loc[row_index], shift_date)
                        df.at[row_index, 'TotalHours'] = total_hours
                        df.at[row_index, 'BreakDuration'] = break_duration
                        save_data()
                        st.success("Initiated Shift Sequence")

                    for i in range(1, 4):
                        if st.button(f"Break {i} Start", key=f"break_{i}_start_{row_index}") and pd.isna(df.at[row_index, f'Break{i}Start']) and pd.notna(df.at[row_index, 'CheckIn']):
                            if i == 1 or (pd.notna(df.at[row_index, f'Break{i-1}End'])):
                                df.at[row_index, f'Break{i}Start'] = format_time(datetime.now(EGYPT_TZ))
                                total_hours, break_duration = calculate_times(df.loc[row_index], shift_date)
                                df.at[row_index, 'TotalHours'] = total_hours
                                df.at[row_index, 'BreakDuration'] = break_duration
                                save_data()
                                st.success(f"Break {i} Sequence Started")

                with col2:
                    for i in range(1, 4):
                        if st.button(f"Break {i} End", key=f"break_{i}_end_{row_index}") and pd.notna(df.at[row_index, f'Break{i}Start']) and pd.isna(df.at[row_index, f'Break{i}End']):
                            df.at[row_index, f'Break{i}End'] = format_time(datetime.now(EGYPT_TZ))
                            total_hours, break_duration = calculate_times(df.loc[row_index], shift_date)
                            df.at[row_index, 'TotalHours'] = total_hours
                            df.at[row_index, 'BreakDuration'] = break_duration
                            save_data()
                            st.success(f"Break {i} Sequence Ended")

                    if st.button("Check Out", key=f"check_out_{row_index}") and pd.notna(df.at[row_index, 'CheckIn']) and pd.isna(df.at[row_index, 'CheckOut']):
                        if all(pd.notna(df.at[row_index, f'Break{i}End']) for i in range(1, 4) if pd.notna(df.at[row_index, f'Break{i}Start'])):
                            df.at[row_index, 'CheckOut'] = format_time(datetime.now(EGYPT_TZ))
                            total_hours, break_duration = calculate_times(df.loc[row_index], shift_date)
                            df.at[row_index, 'TotalHours'] = total_hours
                            df.at[row_index, 'BreakDuration'] = break_duration
                            save_data()
                            st.success("Shift Sequence Terminated")
                st.markdown('</div>', unsafe_allow_html=True)

                # Display current session status
                st.markdown('<div class="card"><h3>Current Session Status</h3>', unsafe_allow_html=True)
                status_html = f"""
                <div style="padding:15px; border: 1px solid #00ffea; border-radius: 10px; box-shadow: 0 0 15px #00ffea;">
                    <p><strong>Check In:</strong> <span style="color: #00ffea;">{df.at[row_index, 'CheckIn'] if pd.notna(df.at[row_index, 'CheckIn']) else 'Awaiting'}</span></p>
                    <p><strong>Break 1 Start:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break1Start'] if 'Break1Start' in df.columns and pd.notna(df.at[row_index, 'Break1Start']) else 'Awaiting'}</span></p>
                    <p><strong>Break 1 End:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break1End'] if 'Break1End' in df.columns and pd.notna(df.at[row_index, 'Break1End']) else 'Awaiting'}</span></p>
                    <p><strong>Break 2 Start:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break2Start'] if 'Break2Start' in df.columns and pd.notna(df.at[row_index, 'Break2Start']) else 'Awaiting'}</span></p>
                    <p><strong>Break 2 End:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break2End'] if 'Break2End' in df.columns and pd.notna(df.at[row_index, 'Break2End']) else 'Awaiting'}</span></p>
                    <p><strong>Break 3 Start:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break3Start'] if 'Break3Start' in df.columns and pd.notna(df.at[row_index, 'Break3Start']) else 'Awaiting'}</span></p>
                    <p><strong>Break 3 End:</strong> <span style="color: #00ffea;">{df.at[row_index, 'Break3End'] if 'Break3End' in df.columns and pd.notna(df.at[row_index, 'Break3End']) else 'Awaiting'}</span></p>
                    <p><strong>Check Out:</strong> <span style="color: #00ffea;">{df.at[row_index, 'CheckOut'] if pd.notna(df.at[row_index, 'CheckOut']) else 'Awaiting'}</span></p>
                    <p><strong>Total Hours:</strong> <span style="color: #00ffea;">{df.at[row_index, 'TotalHours']:.2f} hours</span></p>
                    <p><strong>Break Duration:</strong> <span style="color: #00ffea;">{df.at[row_index, 'BreakDuration']:.2f} hours</span></p>
                </div>
                """
                components.html(status_html, height=360)
                st.markdown('</div>', unsafe_allow_html=True)

                # Display all sessions for the current shift date
                if len(user_rows) > 0:
                    st.markdown('<div class="card"><h3>All Sessions Today</h3>', unsafe_allow_html=True)
                    display_df = user_rows[['CheckIn', 'CheckOut', 'Break1Start', 'Break1End', 'Break2Start', 'Break2End', 'Break3Start', 'Break3End', 'TotalHours', 'BreakDuration']].copy()
                    display_df.fillna('Awaiting', inplace=True)
                    st.dataframe(display_df, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "Admin Dashboard":
    st.title("Command Center")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        admin_password = st.text_input("Enter admin password", type="password", placeholder="Access Code...")
        st.markdown('</div>', unsafe_allow_html=True)
    
    if admin_password == "admin123":  # Simple password, change in production
        # Excel upload for data restoration
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Restore Data from Excel")
        uploaded_file = st.file_uploader("Upload Excel file to restore data", type=["xlsx"])
        if uploaded_file:
            if restore_from_excel(uploaded_file):
                st.success("Data restored successfully from Excel!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Editable Data Matrix
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Edit Data Matrix")
        # Filter options
        filter_user = st.selectbox("Filter by User", options=['All'] + sorted(df['User'].unique().tolist()), key='filter_user')
        filter_date = st.selectbox("Filter by Date", options=['All'] + sorted(df['Date'].unique().tolist()), key='filter_date')
        
        filtered_df = df
        if filter_user != 'All':
            filtered_df = filtered_df[filtered_df['User'] == filter_user]
        if filter_date != 'All':
            filtered_df = filtered_df[filtered_df['Date'] == filter_date]
        
        # Ensure time columns are strings before editing
        for col in TIME_COLUMNS:
            filtered_df[col] = filtered_df[col].astype("string").fillna(pd.NA)
        
        # Calculate totals before editing
        for idx, row in filtered_df.iterrows():
            total_hours, break_duration = calculate_times(row, row['Date'])
            filtered_df.at[idx, 'TotalHours'] = total_hours
            filtered_df.at[idx, 'BreakDuration'] = break_duration
        
        # Editable DataFrame
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "User": st.column_config.TextColumn("User"),
                "Date": st.column_config.TextColumn("Date"),
                "CheckIn": st.column_config.TextColumn("Check In", help="Format: HH:MM AM/PM (e.g., 04:00 PM)"),
                "CheckOut": st.column_config.TextColumn("Check Out", help="Format: HH:MM AM/PM"),
                "Break1Start": st.column_config.TextColumn("Break 1 Start", help="Format: HH:MM AM/PM"),
                "Break1End": st.column_config.TextColumn("Break 1 End", help="Format: HH:MM AM/PM"),
                "Break2Start": st.column_config.TextColumn("Break 2 Start", help="Format: HH:MM AM/PM"),
                "Break2End": st.column_config.TextColumn("Break 2 End", help="Format: HH:MM AM/PM"),
                "Break3Start": st.column_config.TextColumn("Break 3 Start", help="Format: HH:MM AM/PM"),
                "Break3End": st.column_config.TextColumn("Break 3 End", help="Format: HH:MM AM/PM"),
                "TotalHours": st.column_config.NumberColumn("Total Hours", disabled=True),
                "BreakDuration": st.column_config.NumberColumn("Break Duration", disabled=True),
                "Active": st.column_config.CheckboxColumn("Active")
            },
            use_container_width=True
        )
        
        if st.button("Save Data Matrix Changes"):
            for idx, row in edited_df.iterrows():
                total_hours, break_duration = calculate_times(row, row['Date'])
                edited_df.at[idx, 'TotalHours'] = total_hours
                edited_df.at[idx, 'BreakDuration'] = break_duration
            # Ensure time columns remain strings
            for col in TIME_COLUMNS:
                edited_df[col] = edited_df[col].astype("string").fillna(pd.NA)
            df.update(edited_df)
            df.loc[edited_df.index] = edited_df
            save_data()
            st.success("Data Matrix updated successfully!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Edit User Session
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Edit User Session")
        edit_user = st.selectbox("Select User to Edit Session", options=['None'] + sorted(df['User'].unique().tolist()), key='edit_user')
        if edit_user != 'None':
            user_sessions = df[df['User'] == edit_user]
            if not user_sessions.empty:
                session_dates = sorted(user_sessions['Date'].unique().tolist())
                edit_date = st.selectbox("Select Session Date", options=session_dates, key='edit_date')
                session_row = user_sessions[user_sessions['Date'] == edit_date].iloc[-1]
                session_index = session_row.name

                with st.form(key=f"edit_session_form_{session_index}"):
                    st.write(f"Editing session for {edit_user} on {edit_date}")
                    check_in = st.text_input("Check In", value=session_row['CheckIn'] if pd.notna(session_row['CheckIn']) else "", placeholder="e.g., 04:00 PM")
                    break1_start = st.text_input("Break 1 Start", value=session_row['Break1Start'] if pd.notna(session_row['Break1Start']) else "", placeholder="e.g., 06:00 PM")
                    break1_end = st.text_input("Break 1 End", value=session_row['Break1End'] if pd.notna(session_row['Break1End']) else "", placeholder="e.g., 06:30 PM")
                    break2_start = st.text_input("Break 2 Start", value=session_row['Break2Start'] if pd.notna(session_row['Break2Start']) else "", placeholder="e.g., 08:00 PM")
                    break2_end = st.text_input("Break 2 End", value=session_row['Break2End'] if pd.notna(session_row['Break2End']) else "", placeholder="e.g., 08:30 PM")
                    break3_start = st.text_input("Break 3 Start", value=session_row['Break3Start'] if pd.notna(session_row['Break3Start']) else "", placeholder="e.g., 10:00 PM")
                    break3_end = st.text_input("Break 3 End", value=session_row['Break3End'] if pd.notna(session_row['Break3End']) else "", placeholder="e.g., 10:30 PM")
                    check_out = st.text_input("Check Out", value=session_row['CheckOut'] if pd.notna(session_row['CheckOut']) else "", placeholder="e.g., 12:00 AM")
                    active = st.checkbox("Active", value=session_row['Active'])

                    if st.form_submit_button("Save Session Changes"):
                        # Validate time format
                        time_fields = [check_in, check_out, break1_start, break1_end, break2_start, break2_end, break3_start, break3_end]
                        valid = True
                        for field in time_fields:
                            if field:
                                try:
                                    datetime.strptime(f"{edit_date} {field}", "%Y-%m-%d %I:%M %p")
                                except ValueError:
                                    st.error(f"Invalid time format for {field}. Use HH:MM AM/PM (e.g., 04:00 PM).")
                                    valid = False
                        if valid:
                            df.at[session_index, 'CheckIn'] = check_in if check_in else pd.NA
                            df.at[session_index, 'CheckOut'] = check_out if check_out else pd.NA
                            df.at[session_index, 'Break1Start'] = break1_start if break1_start else pd.NA
                            df.at[session_index, 'Break1End'] = break1_end if break1_end else pd.NA
                            df.at[session_index, 'Break2Start'] = break2_start if break2_start else pd.NA
                            df.at[session_index, 'Break2End'] = break2_end if break2_end else pd.NA
                            df.at[session_index, 'Break3Start'] = break3_start if break3_start else pd.NA
                            df.at[session_index, 'Break3End'] = break3_end if break3_end else pd.NA
                            df.at[session_index, 'Active'] = active
                            total_hours, break_duration = calculate_times(df.loc[session_index], edit_date)
                            df.at[session_index, 'TotalHours'] = total_hours
                            df.at[session_index, 'BreakDuration'] = break_duration
                            # Ensure time columns remain strings
                            for col in TIME_COLUMNS:
                                df[col] = df[col].astype("string").fillna(pd.NA)
                            save_data()
                            st.success(f"Session for {edit_user} on {edit_date} updated successfully!")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # User management: Add new user
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("User Management")
        new_user = st.text_input("Add new user (optional)", placeholder="New User Identity...")
        if st.button("Add User") and new_user:
            user_records = df[df['User'] == new_user]
            if user_records.empty or not user_records['Active'].any():
                new_row = {
                    'User': new_user,
                    'Date': str(get_shift_date()),
                    'Active': True,
                    'CheckIn': pd.NA,
                    'CheckOut': pd.NA,
                    'Break1Start': pd.NA,
                    'Break1End': pd.NA,
                    'Break2Start': pd.NA,
                    'Break2End': pd.NA,
                    'Break3Start': pd.NA,
                    'Break3End': pd.NA,
                    'TotalHours': 0.0,
                    'BreakDuration': 0.0
                }
                new_row_df = pd.DataFrame([new_row]).astype({
                    'User': 'string',
                    'Date': 'string',
                    'CheckIn': 'string',
                    'CheckOut': 'string',
                    'Break1Start': 'string',
                    'Break1End': 'string',
                    'Break2Start': 'string',
                    'Break2End': 'string',
                    'Break3Start': 'string',
                    'Break3End': 'string',
                    'TotalHours': 'float64',
                    'BreakDuration': 'float64',
                    'Active': 'boolean'
                })
                df = pd.concat([df, new_row_df], ignore_index=True)
                save_data()
                st.success(f"User {new_user} Authorized")
                st.rerun()
            else:
                st.warning(f"User {new_user} already exists and is active.")
        st.markdown('</div>', unsafe_allow_html=True)

        # User management: Remove user
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Remove User")
        remove_user = st.selectbox("Select User to Remove", options=['None'] + sorted(df['User'].unique().tolist()), key='remove_user')
        action = st.selectbox("Action", options=["Keep User", "Delete User (Keep Data)", "Delete User and Data"], key='user_action')
        
        if st.button("Execute Action") and remove_user != 'None':
            user_records = df[df['User'] == remove_user]
            if user_records.empty:
                st.error(f"User {remove_user} not found.")
            else:
                if action == "Delete User (Keep Data)":
                    df.loc[df['User'] == remove_user, 'Active'] = False
                    save_data()
                    st.success(f"User {remove_user} deleted. Historical data retained.")
                elif action == "Delete User and Data":
                    df = df[df['User'] != remove_user]
                    save_data()
                    st.success(f"User {remove_user} and all associated data deleted.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Download Excel
        def get_excel_download_link(df):
            with pd.ExcelWriter('attendance.xlsx', engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='DataMatrix')
            with open('attendance.xlsx', 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            return f'<a href="data:application/octet-stream;base64,{b64}" download="attendance.xlsx">Download Data Matrix</a>'
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(get_excel_download_link(df), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("Access Denied")

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64
import plotly.express as px
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

# File to store data
DATA_FILE = 'attendance_data.csv'

# Define expected columns
EXPECTED_COLUMNS = ['User', 'Date', 'CheckIn', 'CheckOut', 
                    'Break1Start', 'Break1End', 'Break2Start', 'Break2End', 
                    'Break3Start', 'Break3End', 'TotalHours', 'BreakDuration', 'Active']

# Load data and ensure all columns exist
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            if col == 'Active':
                df[col] = True  # Default all existing users to active
            else:
                df[col] = pd.NA
else:
    df = pd.DataFrame(columns=EXPECTED_COLUMNS)

# Function to save data
def save_data():
    df.to_csv(DATA_FILE, index=False)

# Function to calculate shift date (shift starts at 4 PM, ends at 12 AM next day, but date is the start day)
def get_shift_date():
    now = datetime.now()
    if now.hour < 4 or (now.hour == 4 and now.minute == 0):
        return (now - timedelta(days=1)).date()
    else:
        return now.date()

# Function to format time as 12-hour string (e.g., "12:45 AM")
def format_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")

# Function to parse time string with shift date for calculations
def parse_time(time_str, shift_date):
    if pd.isna(time_str):
        return None
    dt = datetime.strptime(f"{shift_date} {time_str}", "%Y-%m-%d %I:%M %p")
    if dt.hour < 16 and time_str.endswith("AM"):
        dt += timedelta(days=1)
    return dt

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

    /* Sidebar */
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

    /* Headers */
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

    /* Cards */
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

    /* Buttons */
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

    /* Inputs and Selectbox */
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

    /* Dataframe */
    .dataframe {
        background: rgba(255, 255, 255, 0.05);
        color: #ffffff;
        border-radius: 10px;
        border: 1px solid rgba(0, 255, 234, 0.3);
    }

    /* Animations */
    @keyframes slideIn {
        from { transform: translateX(-30px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    .stMarkdown, .stButton, .stTextInput, .stSelectbox {
        animation: slideIn 0.7s ease-out;
    }

    /* Success/Error Messages */
    .stAlert {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid #00ffea;
        border-radius: 10px;
        color: #ffffff;
        box-shadow: 0 0 10px rgba(0, 255, 234, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

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
        user_name = st.text_input("Enter your name", placeholder="Your Identity Code...")
        st.markdown('</div>', unsafe_allow_html=True)

    if user_name:
        # Check if user is active
        user_records = df[df['User'] == user_name]
        user_active = user_records['Active'].any() if not user_records.empty else True
        if not user_active:
            st.error("Access Denied: User account has been deleted.")
        else:
            shift_date = get_shift_date()
            user_rows = df[(df['User'] == user_name) & (df['Date'] == str(shift_date))]

            # Create a new record for each check-in
            if st.button("Start New Session", key="start_session"):
                new_row = {'User': user_name, 'Date': str(shift_date), 'Active': True}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data()
                st.success("New Session Initialized")
                user_rows = df[(df['User'] == user_name) & (df['Date'] == str(shift_date))]

            if not user_rows.empty:
                row_index = user_rows.index[-1]  # Most recent record
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns(2, gap="medium")

                with col1:
                    if st.button("Check In", key=f"check_in_{row_index}") and pd.isna(df.at[row_index, 'CheckIn']):
                        df.at[row_index, 'CheckIn'] = format_time(datetime.now())
                        save_data()
                        st.success("Initiated Shift Sequence")

                    for i in range(1, 4):
                        if st.button(f"Break {i} Start", key=f"break_{i}_start_{row_index}") and pd.isna(df.at[row_index, f'Break{i}Start']) and pd.notna(df.at[row_index, 'CheckIn']):
                            if i == 1 or (pd.notna(df.at[row_index, f'Break{i-1}End'])):
                                df.at[row_index, f'Break{i}Start'] = format_time(datetime.now())
                                save_data()
                                st.success(f"Break {i} Sequence Started")

                with col2:
                    for i in range(1, 4):
                        if st.button(f"Break {i} End", key=f"break_{i}_end_{row_index}") and pd.notna(df.at[row_index, f'Break{i}Start']) and pd.isna(df.at[row_index, f'Break{i}End']):
                            df.at[row_index, f'Break{i}End'] = format_time(datetime.now())
                            save_data()
                            st.success(f"Break {i} Sequence Ended")

                    if st.button("Check Out", key=f"check_out_{row_index}") and pd.notna(df.at[row_index, 'CheckIn']) and pd.isna(df.at[row_index, 'CheckOut']):
                        if all(pd.notna(df.at[row_index, f'Break{i}End']) for i in range(1, 4) if pd.notna(df.at[row_index, f'Break{i}Start'])):
                            df.at[row_index, 'CheckOut'] = format_time(datetime.now())
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
                </div>
                """
                components.html(status_html, height=320)
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
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Data Matrix")
        
        # Calculate totals for all rows
        for idx, row in df.iterrows():
            total_hours, break_duration = calculate_times(row, row['Date'])
            df.at[idx, 'TotalHours'] = total_hours
            df.at[idx, 'BreakDuration'] = break_duration
        save_data()
        
        # Filter options
        st.markdown('<div class="card">', unsafe_allow_html=True)
        filter_user = st.selectbox("Filter by User", options=['All'] + sorted(df['User'].unique().tolist()), key='filter_user')
        filter_date = st.selectbox("Filter by Date", options=['All'] + sorted(df['Date'].unique().tolist()), key='filter_date')
        
        filtered_df = df
        if filter_user != 'All':
            filtered_df = filtered_df[filtered_df['User'] == filter_user]
        if filter_date != 'All':
            filtered_df = filtered_df[filtered_df['Date'] == filter_date]
        
        st.dataframe(filtered_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Interactive chart
        if not filtered_df.empty:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fig = px.bar(filtered_df, x='User', y='TotalHours', color='Date', title='Shift Analytics',
                         color_discrete_sequence=['#00ffea', '#ff00ff', '#00b4d8'],
                         template='plotly_dark')
            fig.update_layout(
                font=dict(family="Orbitron", size=14, color="#00ffea"),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # User management: Add new user
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("User Management")
        new_user = st.text_input("Add new user (optional)", placeholder="New User Identity...")
        if st.button("Add User") and new_user:
            user_records = df[df['User'] == new_user]
            if user_records.empty or not user_records['Active'].any():
                new_row = {'User': new_user, 'Date': str(get_shift_date()), 'Active': True}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data()
                st.success(f"User {new_user} Authorized")
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
                st.rerun()  # Refresh to update dropdowns
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download Excel
        def get_excel_download_link(df):
            output = pd.ExcelWriter('attendance.xlsx', engine='xlsxwriter')
            df.to_excel(output, index=False, sheet_name='DataMatrix')
            output.close()
            with open('attendance.xlsx', 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            return f'<a href="data:application/octet-stream;base64,{b64}" download="attendance.xlsx">Download Data Matrix</a>'
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(get_excel_download_link(filtered_df), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("Access Denied")

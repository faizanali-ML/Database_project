import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from datetime import date
import time
from sqlalchemy import create_engine, text 
from sqlalchemy.exc import SQLAlchemyError
import pymysql
import warnings

# Suppress pandas/library warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- Configuration & Theme ---
st.set_page_config(
    page_title="Hospital Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme Professional Color Palette & Custom CSS 
st.markdown("""
<style>
    /* 1. Dark Background Theme */
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    /* 2. Main Header Style */
    .main-header { font-size: 2.5rem; color: #60a5fa; text-align: left; padding: 10px 0; margin-bottom: 0.5rem; font-weight: 700; }
    /* 3. All text elements */
    h1, h2, h3, h4, h5, h6 { color: #f8fafc !important; }
    p, div, span, label { color: #e2e8f0 !important; }
    /* 4. Streamlit components styling */
    .stButton>button { color: #0f172a !important; background-color: #60a5fa !important; border-radius: 5px; border: none; font-weight: 600; }
    .stButton>button:hover { background-color: #3b82f6 !important; color: #ffffff !important; }
    /* 5. Metric Card Style */
    .metric-card { background-color: #1e293b; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); margin-bottom: 1rem; transition: transform 0.3s ease-in-out; border: 1px solid #334155; }
    .metric-card:hover { transform: translateY(-5px); }
    /* Metric card text colors */
    .metric-card h3 { font-size: 1rem; color: #94a3b8 !important; margin-top: 0; font-weight: 500; }
    .metric-card h2 { font-size: 2.5rem; color: #f8fafc !important; margin: 0.2rem 0; font-weight: 700; }
    .metric-card p { color: #94a3b8 !important; margin: 0; }
    /* 6. Metric Card Color Stripes */
    .metric-card.patients { border-left: 5px solid #60a5fa; } 
    .metric-card.doctors { border-left: 5px solid #34d399; } 
    .metric-card.checks { border-left: 5px solid #fbbf24; } 
    .metric-card.diagnoses { border-left: 5px solid #f87171; } 
    /* Remove Streamlit footer and menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] { background-color: #1e293b; border-right: 1px solid #334155; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] div, [data-testid="stSidebar"] label { color: #e2e8f0 !important; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea { background-color: #334155 !important; color: #e2e8f0 !important; border: 1px solid #475569 !important; }
    .stTabs [aria-selected="true"] { background-color: #60a5fa !important; color: #0f172a !important; }
</style>
""", unsafe_allow_html=True)


# --- MySQL Database Configuration ---
MYSQL_HOST = 'localhost'         
MYSQL_USER = 'root'              
MYSQL_PASSWORD = 'KhanMansoor1' 
MYSQL_DATABASE = 'hospitalmanagementsystem'

# MAPPING APP KEYS TO SQL TABLE NAMES 
TABLE_NAMES_MAP = {
    'checks': 'checks',      
    'doctors': 'doctors',     
    'hospital': 'hospital', 
    'patients': 'patients',   
    'medication': 'medication', 
    'visits': 'visits',       
    'lab_dataset': 'lab_dataset' 
}

# --- Database Connection and Loading (SQLAlchemy implementation for robustness) ---

@st.cache_resource
def get_db_engine():
    """Creates a SQLAlchemy engine for persistent database access."""
    try:
        engine = create_engine(
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}",
            pool_recycle=3600 
        )
        with engine.connect():
            st.sidebar.success(" MySQL Connection Engine Created.")
        return engine
    except Exception as err:
        st.sidebar.error(f" MySQL Engine Error: Please ensure XAMPP is running and credentials are correct. Error: {err}")
        return None

@st.cache_data(show_spinner="Connecting to MySQL and loading data...")
def load_sql_data():
    """Load all necessary tables from the MySQL database into DataFrames using SQLAlchemy."""
    data = {}
    engine = get_db_engine()
    if engine is None:
        return {key: pd.DataFrame() for key in TABLE_NAMES_MAP.keys()}
    
    with engine.connect() as conn:
        for key, table_name in TABLE_NAMES_MAP.items():
            query = f"SELECT * FROM `{table_name}`"
            
            try:
                df = pd.read_sql(query, conn)
                
                # --- POST-LOAD COLUMN TRANSFORMATIONS (DB column name fixes) ---
                if key == 'doctors':
                    # FIX 1: Rename the misspelled DB column 'speacilization' to 'specialization' for display
                    if 'speacilization' in df.columns:
                         df.rename(columns={'speacilization': 'specialization'}, inplace=True)
                    # FIX 2: Rename the DB's case-sensitive 'Name' column to 'name' for internal consistency
                    if 'Name' in df.columns:
                         df.rename(columns={'Name': 'name'}, inplace=True)
                
                date_cols = {'checks': 'check_date', 'visits': 'visit_date', 'medication': 'medication_date', 'lab_dataset': 'test_date'}
                date_col_name = date_cols.get(key)
                if date_col_name and date_col_name in df.columns:
                    df[date_col_name] = pd.to_datetime(df[date_col_name], errors='coerce')

                data[key] = df
                
            except SQLAlchemyError as e:
                st.sidebar.warning(f" Error loading table '{table_name}'. Please ensure the table exists in MySQL. Error: {e}")
                data[key] = pd.DataFrame()
            except Exception as e:
                 st.sidebar.error(f" Unforeseen Error processing data for table {table_name}: {str(e)}")
                 data[key] = pd.DataFrame()
    
    return data

def save_dataframe_to_sql(key, df):
    """Saves an entire DataFrame back to its corresponding MySQL table using SQLAlchemy Engine."""
    table_name = TABLE_NAMES_MAP.get(key)
    if table_name:
        engine = get_db_engine()
        if engine is None: return 

        try:
            # --- PRE-SAVE COLUMN TRANSFORMATIONS (Reverse DB column name fixes) ---
            df_to_save = df.copy()

            if key == 'doctors':
                # FIX 1: Rename 'specialization' back to the DB's column name 'speacilization'
                if 'specialization' in df_to_save.columns:
                     df_to_save.rename(columns={'specialization': 'speacilization'}, inplace=True)
                
                # FIX 2: Rename internal 'name' back to the DB's case-sensitive 'Name' column
                if 'name' in df_to_save.columns:
                    df_to_save.rename(columns={'name': 'Name'}, inplace=True)
                 
                # Ensure 'Name' handles empty strings by converting them to None/NULL
                if 'Name' in df_to_save.columns: 
                     df_to_save['Name'] = df_to_save['Name'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)
                 
            # Date Formatting (MySQL expects date strings for date columns)
            date_cols = {'checks': 'check_date', 'visits': 'visit_date', 'medication': 'medication_date', 'lab_dataset': 'test_date'}
            date_col_name = date_cols.get(key)
            if date_col_name and date_col_name in df_to_save.columns and pd.api.types.is_datetime64_any_dtype(df_to_save[date_col_name]):
                df_to_save[date_col_name] = df_to_save[date_col_name].dt.strftime('%Y-%m-%d')
            
            # Use pandas to_sql with the SQLAlchemy engine object 
            df_to_save.to_sql(table_name, engine, if_exists='replace', index=False)
            
            st.toast(f"💾 **Success!** New record saved to **{table_name.upper()}** table.", icon='✅')
            
            st.cache_data.clear()
            time.sleep(1) 
            st.rerun()
            
        except SQLAlchemyError as e:
            st.error(f"Error saving data to MySQL table {table_name} (SQLAlchemy Error): {e}")
        except Exception as e:
            st.error(f"Error saving data: {e}")
    else:
        st.error(f"SQL Table name not found for key: {key}")

def delete_record_from_sql(key, primary_key_col, record_id):
    """Deletes a single record from a specified SQL table based on its primary key and ID using SQLAlchemy."""
    table_name = TABLE_NAMES_MAP.get(key)
    if not table_name:
        st.error(f"SQL Table name not found for key: {key}")
        return

    engine = get_db_engine()
    if engine is None: return

    # FIX FOR PYTHON SYNTAX ERROR (Ensuring try is followed by except/finally)
    try:
        # Use engine.connect() for transactional execution
        with engine.connect() as conn:
            delete_query = text(f"DELETE FROM `{table_name}` WHERE `{primary_key_col}` = :record_id")
            
            # Execute the query, passing the parameter safely
            result = conn.execute(delete_query, {"record_id": record_id})
            
            # Commit the transaction explicitly
            conn.commit()

            if result.rowcount > 0:
                st.toast(f"🗑️ **Success!** Record with {primary_key_col}='{record_id}' deleted from **{table_name.upper()}**.", icon='✅')
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.warning(f"Record with ID '{record_id}' not found in table **{table_name.upper()}**.")

    except SQLAlchemyError as e:
        st.error(f"Error deleting data from MySQL table {table_name} (SQLAlchemy Error): {e}")
    except Exception as e:
        st.error(f"Error during deletion: {e}")

# --- Dashboard Functions (Retained from previous working version) ---

def create_metrics_row(data):
    """Create a row of metric cards using real data"""
    col1, col2, col3, col4 = st.columns(4)
    
    total_patients = len(data.get('patients', pd.DataFrame()))
    total_doctors = len(data.get('doctors', pd.DataFrame()))
    total_checks = len(data.get('checks', pd.DataFrame()))
    unique_diagnoses = data['checks']['diagnosis'].nunique() if 'diagnosis' in data.get('checks', pd.DataFrame()).columns else 0

    with col1:
        st.markdown(f"""
        <div class="metric-card patients">
            <h3>👥 Total Patients</h3>
            <h2>{total_patients}</h2>
            <p>Unique individuals in system</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card doctors">
            <h3>👨‍⚕️ Medical Staff</h3>
            <h2>{total_doctors}</h2>
            <p>Active doctors registered</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card checks">
            <h3>📊 Total Checks</h3>
            <h2>{total_checks}</h2>
            <p>Patient examinations recorded</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card diagnoses">
            <h3>🔬 Diagnosis Types</h3>
            <h2>{unique_diagnoses}</h2>
            <p>Different conditions treated</p>
        </div>
        """, unsafe_allow_html=True)

def create_charts(data):
    """Create visualization charts using real data"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top 10 Diagnosis Distribution 📉")
        checks_df = data.get('checks', pd.DataFrame())
        if not checks_df.empty and 'diagnosis' in checks_df.columns:
            diagnosis_counts = checks_df['diagnosis'].value_counts().head(10)
            fig_diagnosis = px.pie(
                values=diagnosis_counts.values,
                names=diagnosis_counts.index,
                title='<span style="font-size: 14px; color: #94a3b8;">Percentage of All Checks</span>',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_diagnosis.update_layout(
                height=400, 
                margin=dict(t=50, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig_diagnosis, use_container_width=True)
        else:
            st.info("No checks data available for diagnosis chart")
    
    with col2:
        st.subheader("Monthly Patient Checks Trend 📈")
        checks_df = data.get('checks', pd.DataFrame())
        if not checks_df.empty and 'check_date' in checks_df.columns and pd.api.types.is_datetime64_any_dtype(checks_df['check_date']):
            try:
                monthly_checks = checks_df.groupby(
                    checks_df['check_date'].dt.to_period('M')
                ).size().reset_index(name='count')
                monthly_checks['check_date'] = monthly_checks['check_date'].dt.to_timestamp()
                
                fig_trend = px.line(
                    monthly_checks,
                    x='check_date',
                    y='count',
                    title='<span style="font-size: 14px; color: #94a3b8;">Volume of checks over time</span>',
                    markers=True,
                    color_discrete_sequence=['#60a5fa']
                )
                fig_trend.update_layout(
                    height=400, 
                    xaxis_title='Month', 
                    yaxis_title='Checks Count', 
                    margin=dict(t=50, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    xaxis=dict(gridcolor='#334155'),
                    yaxis=dict(gridcolor='#334155')
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate trend chart: {e}")
        else:
            st.info("No date data available for trend chart")

def create_tables(data):
    """Create data tables using real data"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Patient Checks 📋")
        checks_df = data.get('checks', pd.DataFrame())
        if not checks_df.empty:
            recent_checks = checks_df.copy()
            if 'check_date' in recent_checks.columns and pd.api.types.is_datetime64_any_dtype(recent_checks['check_date']):
                recent_checks = recent_checks.sort_values('check_date', ascending=False)
            
            st.dataframe(
                recent_checks.head(10).drop(columns=['check_date'], errors='ignore'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No checks data available")
    
    with col2:
        st.subheader("Doctor Specialization Summary 🧑‍🔬")
        doctors_df = data.get('doctors', pd.DataFrame())
        if not doctors_df.empty and 'specialization' in doctors_df.columns:
            spec_summary = doctors_df['specialization'].value_counts().reset_index()
            spec_summary.columns = ['Specialization', 'Count']
            st.dataframe(spec_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No doctors data available")

# --- Enhanced Functionality ---

def search_all_data(data):
    """Allows searching for a term across all DataFrames."""
    st.header("🔍 Global Data Search")
    
    search_term = st.text_input("Enter search term (e.g., patient ID, diagnosis, doctor name):", key="global_search_input").strip()
    
    if not search_term:
        st.info("Enter a term to search across all datasets.")
        return
    
    st.subheader(f"Results for: **'{search_term}'**")
    
    found_any = False
    
    with st.spinner("Searching all datasets..."):
        for key, df in data.items():
            if df.empty:
                continue
                
            # Create a boolean mask where the search term is found in any column (converted to string)
            mask = df.astype(str).apply(
                lambda col: col.str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            
            results = df[mask]
            
            if not results.empty:
                st.markdown(f"**Found {len(results)} matches in the `{key.upper()}` dataset:**")
                st.dataframe(results, use_container_width=True, hide_index=True)
                found_any = True

    if not found_any:
        st.warning(f"No matches found for '{search_term}' in any dataset.")

def manage_records(data):
    """Allows adding and deleting records to/from a selected dataset."""
    st.header("➕ / 🗑️ Manage Database Records")
    
    # Use tabs for separation
    tab1, tab2 = st.tabs(["➕ Add New Record", "🗑️ Delete Existing Record"])
    
    valid_keys = list(TABLE_NAMES_MAP.keys()) 

    # --- TAB 1: ADD NEW RECORD LOGIC ---
    with tab1:
        st.subheader("Add New Record")
        dataset_key = st.selectbox("Select Dataset to Add a Record", options=valid_keys, key="add_record_dataset_select")
        if not dataset_key: return st.warning("No datasets defined.")

        # Define columns based on your SQL schema. 
        # Use DB column names 'Name' and 'speacilization' for input to match the database schema
        schema_map = {
            'checks': ['check_id', 'patient_id', 'doctor_id', 'check_date', 'diagnosis'],
            'doctors': ['doctor_id', 'hospital_id', 'Name', 'contact_number', 'speacilization'], 
            'patients': ['patient_id', 'first_name', 'last_name', 'gender', 'age', 'address'], 
            'hospital': ['hospital_id', 'contact_number', 'hospital_address', 'hospital_name'], 
            'medication': ['medication_id', 'check_id', 'manufacture', 'dosage'],
            'visits': ['hospital_id', 'patient_id', 'visit_date', 'discharge_date'], 
            'lab_dataset': ['test_id', 'check_id', 'test_date', 'test_name', 'result'] 
        }
        columns = schema_map.get(dataset_key, [])
        
        st.caption(f"Enter New Record for **{dataset_key.upper()}** with {len(columns)} fields.")
        
        # 2. Input Fields in a Form
        with st.form(key='add_record_form'):
            new_record_data = {}
            cols_per_row = 3
            cols = st.columns(cols_per_row)
            
            for i, col_name in enumerate(columns):
                with cols[i % cols_per_row]:
                    # Helper to show user-friendly names while retaining the DB column name for logic
                    display_name = col_name.replace('speacilization', 'Specialization').replace('_', ' ').title()
                    
                    # Input type logic based on schema
                    if 'date' in col_name.lower():
                        new_record_data[col_name] = st.date_input(f"{display_name}", key=f"input_{dataset_key}_{col_name}", value=datetime.now().date(), help="Select a date.")
                    # Use .lower() for conditional checks to catch DB names like 'Name'
                    elif col_name.lower() in ['diagnosis', 'address', 'result', 'name', 'dosage', 'test_name', 'speacilization', 'manufacture', 'first_name', 'last_name', 'gender', 'hospital_address', 'hospital_name']:
                        new_record_data[col_name] = st.text_input(f"{display_name}", key=f"input_{dataset_key}_{col_name}", help="Enter text value.")
                    elif col_name.lower().endswith('_id') or 'number' in col_name.lower():
                         new_record_data[col_name] = st.text_input(f"{display_name} (ID/Number)", key=f"input_{dataset_key}_{col_name}", help="Enter ID or Contact Number.")
                    elif col_name.lower() == 'age':
                        new_record_data[col_name] = st.number_input(f"{display_name}", min_value=1, max_value=150, step=1, key=f"input_{dataset_key}_{col_name}", help="Enter patient's age.")
                    else:
                        new_record_data[col_name] = st.text_input(f"{display_name}", key=f"input_{dataset_key}_{col_name}")
                        
            submit_button = st.form_submit_button(label='Add Record and Save to SQL', type="primary")
            
            if submit_button:
                row_dict = {}
                valid_input = True
                for col_name in columns:
                    value = new_record_data.get(col_name)
                    
                    if isinstance(value, date):
                        row_dict[col_name] = value.strftime('%Y-%m-%d')
                    elif value is None or (isinstance(value, str) and value.strip() == ''):
                        if col_name.lower().endswith('_id') or col_name.lower() in ['first_name', 'name', 'diagnosis']:
                             st.error(f"The critical field '{col_name}' cannot be empty.")
                             valid_input = False
                             break
                        row_dict[col_name] = None
                    else:
                        if col_name.lower() == 'age' and isinstance(value, int):
                            row_dict[col_name] = value
                        else:
                            row_dict[col_name] = str(value).strip()
                        
                if not valid_input: return
                
                try:
                    current_data_full = load_sql_data() 
                    current_df = current_data_full.get(dataset_key, pd.DataFrame(columns=columns))
                    
                    # CRITICAL FIX for doctors table: 
                    # Rename input keys to match the DataFrame's internal column names ('specialization' and 'name')
                    if dataset_key == 'doctors':
                        if 'speacilization' in row_dict:
                            row_dict['specialization'] = row_dict.pop('speacilization')
                        # FIX: Rename the DB column 'Name' from form input to DataFrame column 'name'
                        if 'Name' in row_dict: 
                            row_dict['name'] = row_dict.pop('Name') 
                    
                    # Create the new row as a DataFrame, using existing columns to ensure order
                    new_row_df = pd.DataFrame([row_dict], columns=current_df.columns) 
                    
                    updated_df = pd.concat([current_df, new_row_df], ignore_index=True)
                    save_dataframe_to_sql(dataset_key, updated_df)
                    
                except Exception as e:
                    st.error(f"Failed to process and save record: {e}")

    # --- TAB 2: DELETE EXISTING RECORD LOGIC ---
    with tab2:
        st.subheader("Delete Existing Record")
        st.warning("⚠️ **Caution:** Deleting a record is permanent and cannot be undone. Always verify the ID.")

        # Determine Primary Key columns for selection help
        primary_key_map = {
            'checks': 'check_id',
            'doctors': 'doctor_id',
            'patients': 'patient_id',
            'hospital': 'hospital_id',
            'medication': 'medication_id',
            'visits': 'patient_id', 
            'lab_dataset': 'test_id'
        }
        
        delete_key = st.selectbox("Select Dataset to Delete a Record From", options=valid_keys, key="delete_record_dataset_select")
        
        if delete_key:
            pk_col = primary_key_map.get(delete_key, 'patient_id') 
            
            st.markdown(f"**Primary Key Column:** `{pk_col}` (The unique identifier for this table)")
            
            with st.expander(f"View Current **{delete_key.upper()}** Records"):
                 df_to_view = data.get(delete_key, pd.DataFrame())
                 if not df_to_view.empty:
                    st.dataframe(df_to_view, use_container_width=True, hide_index=True)
                 else:
                    st.info("The table is currently empty.")
            
            with st.form(key='delete_record_form'):
                record_id_to_delete = st.text_input(
                    f"Enter the **{pk_col}** of the record to delete (e.g., 'P001', 'D005'):", 
                    key="delete_id_input", 
                    help=f"This must be the exact value in the `{pk_col}` column."
                )
                
                delete_button = st.form_submit_button(label=f'Permanently Delete {delete_key.upper()} Record', type="primary")

                if delete_button:
                    if record_id_to_delete.strip():
                        col_to_delete_by = primary_key_map.get(delete_key, 'patient_id') 
                        delete_record_from_sql(delete_key, col_to_delete_by, record_id_to_delete.strip())
                    else:
                        st.error("Please enter a valid record ID to delete.")

def patient_management(data):
    """Patient Management Section using real data"""
    st.header("👤 Patient Management")
    
    patients_df = data.get('patients', pd.DataFrame())
    checks_df = data.get('checks', pd.DataFrame())
    
    if patients_df.empty:
        st.info("No patient data available.")
        return
    
    if not checks_df.empty and 'patient_id' in patients_df.columns and 'patient_id' in checks_df.columns:
        checks_df['check_date'] = pd.to_datetime(checks_df['check_date'], errors='coerce')
        latest_checks = checks_df.sort_values('check_date', ascending=False).drop_duplicates(subset=['patient_id'])
        
        display_df = patients_df.merge(
            latest_checks[['patient_id', 'diagnosis']], 
            on='patient_id', 
            how='left'
        ).rename(columns={'diagnosis': 'Latest Diagnosis'})
    else:
        display_df = patients_df.copy()
        
    # Search and filters
    col1, col2, col3 = st.columns(3)
    with col1:
        patient_id_col = 'patient_id'
        search_term = st.text_input(f"Search by {patient_id_col}, Name, or Address", key="patient_search")
    with col2:
        diagnosis_options = ["All"] + list(display_df['Latest Diagnosis'].dropna().unique()) if 'Latest Diagnosis' in display_df.columns else ["All"]
        diagnosis_filter = st.selectbox("Filter by Latest Diagnosis", diagnosis_options, key="diagnosis_filter")
    with col3:
        if st.button("Refresh Data/Clear Filters", type="secondary"):
            st.rerun()
    
    # Filter data
    filtered_patients = display_df.copy()
    
    if search_term:
        filtered_patients = filtered_patients.astype(str).apply(
            lambda col: col.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        filtered_patients = display_df[filtered_patients]
    
    if diagnosis_filter != "All" and 'Latest Diagnosis' in filtered_patients.columns:
        filtered_patients = filtered_patients[filtered_patients['Latest Diagnosis'] == diagnosis_filter]
    
    st.markdown("---")

    # Display patient checks table
    st.subheader("Patient Directory")
    st.dataframe(
        filtered_patients,
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")

    # Patient statistics
    st.subheader("Patient Key Statistics (Filtered)")
    colA, colB, colC, colD = st.columns(4)
    
    with colA:
        st.metric("Total Patients (Filtered)", len(filtered_patients))
    with colB:
        if not checks_df.empty and 'patient_id' in checks_df.columns:
             unique_visits = checks_df[checks_df['patient_id'].isin(filtered_patients['patient_id'])]['patient_id'].count()
        else:
             unique_visits = len(filtered_patients)
        st.metric("Total Checks/Visits", unique_visits)
    with colC:
        if 'Latest Diagnosis' in filtered_patients.columns and len(filtered_patients) > 0:
            most_common = filtered_patients['Latest Diagnosis'].mode().iloc[0] if not filtered_patients['Latest Diagnosis'].mode().empty else "N/A"
        else:
            most_common = "N/A"
        st.metric("Most Common Diagnosis", most_common)
    with colD:
        if 'age' in filtered_patients.columns and len(filtered_patients) > 0:
            avg_age = filtered_patients['age'].astype(float).mean().round(1)
        else:
            avg_age = "N/A"
        st.metric("Average Age", avg_age)

def doctor_management(data):
    """Doctor Management Section using real data"""
    st.header("👨‍⚕️ Medical Staff Management")
    
    doctors_df = data.get('doctors', pd.DataFrame())
    checks_df = data.get('checks', pd.DataFrame())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Doctors by Specialization")
        if not doctors_df.empty and 'specialization' in doctors_df.columns:
            spec_counts = doctors_df['specialization'].value_counts()
            fig_spec = px.bar(
                x=spec_counts.values,
                y=spec_counts.index,
                orientation='h',
                title='<span style="font-size: 14px; color: #94a3b8;">Count of Doctors in Each Area</span>',
                color=spec_counts.values,
                color_continuous_scale='Mint'
            )
            fig_spec.update_layout(
                height=400, 
                showlegend=False, 
                margin=dict(t=50, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                xaxis=dict(gridcolor='#334155'),
                yaxis=dict(gridcolor='#334155')
            )
            st.plotly_chart(fig_spec, use_container_width=True)
        else:
            st.info("No doctors data available for chart")
    
    with col2:
        st.subheader("Top Performing Doctors")
        if not checks_df.empty and not doctors_df.empty and 'doctor_id' in checks_df.columns:
            doctor_activity = checks_df['doctor_id'].value_counts().head(10).reset_index()
            doctor_activity.columns = ['doctor_id', 'patient_count']
            
            if 'doctor_id' in doctors_df.columns and 'name' in doctors_df.columns: 
                name_col = 'name' 

                doctor_activity = doctor_activity.merge(
                    doctors_df[['doctor_id', name_col]], 
                    on='doctor_id', 
                    how='left'
                ).sort_values('patient_count', ascending=True) 
                
                if doctor_activity[name_col].isnull().any():
                    doctor_activity[name_col] = doctor_activity[name_col].fillna(doctor_activity['doctor_id'].astype(str) + " (ID Missing)")

                fig_activity = px.bar(
                    doctor_activity,
                    x='patient_count',
                    y=name_col,
                    orientation='h',
                    title='<span style="font-size: 14px; color: #94a3b8;">Patient Checks Volume</span>',
                    color='patient_count',
                    color_continuous_scale='Teal'
                )
                fig_activity.update_layout(
                    height=400, 
                    showlegend=False, 
                    margin=dict(t=50, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    xaxis=dict(gridcolor='#334155'),
                    yaxis=dict(gridcolor='#334155')
                )
                st.plotly_chart(fig_activity, use_container_width=True)
            else:
                st.info("Doctor name or ID columns are missing for activity chart.")
        else:
            st.info("No data available for doctor activity chart.")
    
    st.markdown("---")

    # Doctors table
    st.subheader("Medical Staff Directory")
    if not doctors_df.empty:
        st.dataframe(
            doctors_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No doctors data available")

def diagnosis_analytics(data):
    """Diagnosis Analytics Section"""
    st.header("🔬 Diagnosis Analytics")
    
    checks_df = data.get('checks', pd.DataFrame())
    
    if checks_df.empty or 'diagnosis' not in checks_df.columns:
        st.warning("No checks data available for diagnosis analytics.")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Diagnoses Monthly Trend")
        if 'check_date' in checks_df.columns and pd.api.types.is_datetime64_any_dtype(checks_df['check_date']):
            try:
                # Diagnosis trends over time
                monthly_diagnosis = checks_df.copy()
                monthly_diagnosis['month'] = monthly_diagnosis['check_date'].dt.to_period('M')
                
                top_diagnoses = monthly_diagnosis['diagnosis'].value_counts().head(5).index
                monthly_trends = monthly_diagnosis[monthly_diagnosis['diagnosis'].isin(top_diagnoses)]
                monthly_trends = monthly_trends.groupby(['month', 'diagnosis']).size().reset_index(name='count')
                monthly_trends['month'] = monthly_trends['month'].dt.to_timestamp()
                
                fig_trends = px.line(
                    monthly_trends,
                    x='month',
                    y='count',
                    color='diagnosis',
                    title='<span style="font-size: 14px; color: #94a3b8;">Frequency of Top 5 Conditions</span>',
                    markers=True,
                    color_discrete_sequence=px.colors.qualitative.Dark24
                )
                fig_trends.update_layout(
                    height=400, 
                    margin=dict(t=50, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    xaxis=dict(gridcolor='#334155'),
                    yaxis=dict(gridcolor='#334155')
                )
                st.plotly_chart(fig_trends, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate trends chart: {e}")
        else:
            st.info("Date data not correctly formatted for trend analysis.")
    
    with col2:
        st.subheader("Diagnosis Frequency Summary")
        
        # Diagnosis statistics
        diagnosis_stats = checks_df['diagnosis'].value_counts().reset_index()
        diagnosis_stats.columns = ['Diagnosis', 'Count']
        total_checks = len(checks_df)
        diagnosis_stats['Percentage'] = (diagnosis_stats['Count'] / total_checks * 100).round(2)
        
        st.dataframe(
            diagnosis_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Percentage": st.column_config.ProgressColumn(
                    "Percentage (%)",
                    format="%.2f",
                    min_value=0,
                    max_value=100,
                    help="Progress bar shows the percentage of total checks."
                ),
            },
        )
        
        st.markdown("---")

        # Quick stats
        st.subheader("Quick Statistics")
        colA, colB = st.columns(2)
        mode_result = checks_df['diagnosis'].mode()
        with colA:
            most_common = mode_result.iloc[0] if not mode_result.empty else "N/A"
            st.metric("Most Common Diagnosis", most_common)
        with colB:
            rarest = diagnosis_stats.iloc[-1]['Diagnosis'] if len(diagnosis_stats) > 0 else "N/A"
            st.metric("Rarest Diagnosis", rarest)

def data_explorer(data):
    """Data Explorer Section"""
    st.header("📂 Data Explorer")
    
    # Generate tabs for all loaded datasets
    tabs = st.tabs([key.upper() for key in data.keys()])
    
    for i, (key, dataset) in enumerate(data.items()):
        with tabs[i]:
            st.subheader(f"{key.upper()} Dataset")
            if not dataset.empty:
                st.info(f"Total Records: {len(dataset)} | Columns: {len(dataset.columns)}")
                st.dataframe(dataset, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No {key} data available in the corresponding SQL table.")

# --- Main Application Logic ---

def main():
    """Main application with improved navigation and RBAC"""
    st.markdown('<h1 class="main-header">Hospital Management System</h1>', unsafe_allow_html=True)
    
    # Load data
    data = load_sql_data() 
    
    # Check if we have at least some data
    has_data = any(not df.empty for df in data.values())
    
    if not has_data and get_db_engine() is not None:
         st.error("## ⚠️ MySQL connection successful, but all data tables are empty. Please ensure you have data in your tables.")
             
    # --- Sidebar setup (Logo & RBAC) ---
    st.sidebar.title("     System Control")
    
    st.sidebar.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <p style='font-size: 40px; color: #60a5fa; margin: 0; line-height: 1;'>⛨</p> 
            <h3 style='color: #f8fafc; margin-top: 5px; margin-bottom: 0;'>Healthcare Management</h3>
            <p style='font-size: 0.8rem; color: #94a3b8; margin: 0;'>Your Pulse on Hospital Performance</p>
        </div>
        
    """, unsafe_allow_html=True)
    
    # 1. Simple Role-Based Access Control (RBAC)
    st.sidebar.subheader("User Role Selector")
    user_role = st.sidebar.radio(
        "Select your role to view relevant features:",
        options=["Admin", "Doctor", "Patient Desk", "Data Analyst"],
        index=0 
    )
    st.sidebar.markdown("---")
    
    # Define pages and the roles that can access them
    PAGE_ACCESS = {
        "📊 Dashboard Overview": ["Admin", "Doctor", "Patient Desk", "Data Analyst"],
        "👤 Patient Management": ["Admin", "Doctor", "Patient Desk"],
        "👨‍⚕️ Medical Staff": ["Admin", "Doctor", "Data Analyst"],
        "🔬 Diagnosis Analytics": ["Admin", "Data Analyst"],
        "🔍 Global Data Search": ["Admin", "Doctor", "Patient Desk", "Data Analyst"],
        "➕ Manage Records (Add/Delete)": ["Admin", "Patient Desk"], 
        "📂 Data Explorer": ["Admin", "Data Analyst"]
    }
    
    # Filter pages based on the selected role
    available_pages = {
        key: func for key, func in {
            "📊 Dashboard Overview": create_metrics_row, 
            "👤 Patient Management": patient_management,
            "👨‍⚕️ Medical Staff": doctor_management,
            "🔬 Diagnosis Analytics": diagnosis_analytics,
            "🔍 Global Data Search": search_all_data,
            "➕ Manage Records (Add/Delete)": manage_records, 
            "📂 Data Explorer": data_explorer
        }.items() if user_role in PAGE_ACCESS.get(key, [])
    }

    st.sidebar.subheader("System Navigation")
    page_selection = st.sidebar.radio("Go to", list(available_pages.keys()))
    
    st.markdown("---") 
    
    # Execute the selected page function
    if page_selection == "📊 Dashboard Overview":
        # The dashboard page calls multiple functions
        create_metrics_row(data)
        st.markdown("---")
        create_charts(data)
        st.markdown("---")
        create_tables(data)
    else:
        # For all other pages, call the corresponding function directly
        available_pages[page_selection](data)
        
    # --- Footer ---
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Current User Role:** **{user_role}**")
    
if __name__ == "__main__":
    main()
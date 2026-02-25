import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# 1. PAGE SETUP & THEME
st.set_page_config(page_title="Lagos Apps Expense Portal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFDD0; }
    h1, h2, h3, p, span, label { color: #2E7D32 !important; }
    
    .stButton>button, .stFormSubmitButton>button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 10px;
        border: 3px solid #2E7D32;
        padding: 0.6rem 2rem;
        font-weight: 900 !important;
        font-size: 18px !important;
        text-transform: uppercase;
    }
    
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>textarea, .stNumberInput>div>div>input {
        background-color: white !important;
        color: black !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. DATA CONFIGURATION
user_emails = {
    "adekola@mainlandgroup.org": "Adeleke Adekola",
    "ejiro@mainlandgroup.org": "Ejiro"
}

admin_users = ["Jide Olateju", "Stephen Olabinjo", "Esumo Esumo"]

# 3. INITIALIZE CONNECTION & SESSION
conn = st.connection("gsheets", type=GSheetsConnection)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_info = {}

# 4. LOGIN INTERFACE
if not st.session_state.logged_in:
    st.title("🤝 LAGOS APPS EXPENSE REQUEST")
    st.sidebar.title("🏢 Portal Login")
    role_choice = st.sidebar.radio("Login as:", ["User", "Admin"])
    login_input = st.sidebar.text_input("Enter Email (User) or First Name (Admin)").strip().lower()

    if st.sidebar.button("ENTER"):
        if role_choice == "User":
            if login_input in user_emails:
                st.session_state.logged_in = True
                st.session_state.role = "User"
                st.session_state.user_info = {"email": login_input, "name": user_emails[login_input]}
                st.rerun()
            else:
                st.sidebar.error("Email not found.")
        
        elif role_choice == "Admin":
            admin_match = next((name for name in admin_users if name.split()[0].lower() == login_input), None)
            if admin_match:
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.session_state.user_info = {"name": admin_match}
                st.rerun()
            else:
                st.sidebar.error("Admin name not recognized.")

else:
    # LOGOUT
    if st.sidebar.button("LOGOUT"):
        st.session_state.logged_in = False
        st.session_state.user_info = {}
        st.rerun()

    # --- USER INTERFACE ---
    if st.session_state.role == "User":
        st.title(f"Welcome {st.session_state.user_info['name']}!")
        st.subheader("Make Your Request")
        
        tab1, tab2 = st.tabs(["New Request", "Request History"])
        
        with tab1:
            # Removed clear_on_submit=True to prevent premature resetting of fields
            with st.form("expense_form", clear_on_submit=False):
                req_date = st.date_input("Date of Request", date.today(), key="req_date")
                
                # Using unique keys ensures Streamlit preserves the value during reruns
                amount = st.number_input("Amount Requested (₦)", min_value=0.0, format="%.2f", key="amount_input")
                amount_word = st.text_input("Amount in Words", key="amount_word_input")
                
                col1, col2, col3 = st.columns(3)
                b_name = col1.text_input("Beneficiary Name", key="b_name")
                b_bank = col2.text_input("Beneficiary Bank", key="b_bank")
                b_acc = col3.text_input("Account No.", key="b_acc")
                
                reason = st.text_area("Reason for Payment", key="reason")
                receipt = st.file_uploader("Upload Invoice/Receipt (Image/PDF)", type=['png', 'jpg', 'pdf'], key="receipt")
                approver = st.selectbox("Select Approval", admin_users, key="approver")
                
                submit_req = st.form_submit_button("SUBMIT REQUEST")
                
                if submit_req:
                    if amount > 0 and b_name and b_acc:
                        try:
                            new_data = pd.DataFrame([{
                                "Request Date": str(req_date),
                                "Staff Name": st.session_state.user_info['name'],
                                "Email": st.session_state.user_info['email'],
                                "Amount": amount,
                                "Amount in Words": amount_word,
                                "Beneficiary Name": b_name,
                                "Beneficiary Bank": b_bank,
                                "Account No": b_acc,
                                "Reason": reason,
                                "Receipt Link": receipt.name if receipt else "No File",
                                "Approver Name": approver,
                                "Status": "Pending",
                                "Admin Comment": ""
                            }])
                            old_df = conn.read(worksheet="Expense Tracker", ttl=0)
                            updated_df = pd.concat([old_df, new_data], ignore_index=True)
                            conn.update(worksheet="Expense Tracker", data=updated_df)
                            st.success("Request Submitted Successfully!")
                            st.balloons()
                            # Optional: st.rerun() here if you want to clear the form after success
                        except Exception as e:
                            st.error(f"Error connecting to Google Sheets: {e}")
                    else:
                        st.error("Please fill in all required fields (Amount, Beneficiary, and Account No).")

        with tab2:
            st.subheader("Your Transaction History")
            try:
                history_df = conn.read(worksheet="Expense Tracker", ttl=0)
                my_history = history_df[history_df['Email'] == st.session_state.user_info['email']]
                if not my_history.empty:
                    st.dataframe(my_history[::-1], use_container_width=True)
                else:
                    st.info("No history found.")
            except:
                st.warning("Could not load history. Please check your Spreadsheet connection.")

    # --- ADMIN INTERFACE ---
    elif st.session_state.role == "Admin":
        admin_name = st.session_state.user_info['name']
        st.title(f"Admin Dashboard: {admin_name}")
        
        try:
            all_requests = conn.read(worksheet="Expense Tracker", ttl=0)
            # Filter: Only see requests where THIS admin was selected as the approver
            my_tasks = all_requests[all_requests['Approver Name'] == admin_name]
            
            if not my_tasks.empty:
                pending_tasks = my_tasks[my_tasks['Status'] == "Pending"]
                
                st.subheader("Pending Approvals")
                if not pending_tasks.empty:
                    for idx, row in pending_tasks.iterrows():
                        with st.expander(f"Request from {row['Staff Name']} - ₦{row['Amount']}"):
                            st.write(f"**Reason:** {row['Reason']}")
                            st.write(f"**Bank:** {row['Beneficiary Bank']} | **Acc:** {row['Account No']}")
                            
                            comment = st.text_input("Admin Comment", key=f"comm_{idx}")
                            col_a, col_b = st.columns(2)
                            
                            if col_a.button("✅ Approve", key=f"app_{idx}"):
                                all_requests.at[idx, 'Status'] = "Approved"
                                all_requests.at[idx, 'Admin Comment'] = comment
                                conn.update(worksheet="Expense Tracker", data=all_requests)
                                st.success("Approved!")
                                st.rerun()
                                
                            if col_b.button("❌ Decline", key=f"dec_{idx}"):
                                all_requests.at[idx, 'Status'] = "Declined"
                                all_requests.at[idx, 'Admin Comment'] = comment
                                conn.update(worksheet="Expense Tracker", data=all_requests)
                                st.error("Declined!")
                                st.rerun()
                
                st.write("---")
                st.subheader("All My Processed Requests")
                st.dataframe(my_tasks[::-1], use_container_width=True)
                
            else:
                st.info("No requests currently assigned to you.")
        except:
            st.error("Error accessing Spreadsheet. Check Secrets or Tab Name.")

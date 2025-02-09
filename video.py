import streamlit as st
import mysql.connector
import pandas as pd
from datetime import date
import pickle
from st_aggrid import AgGrid, GridOptionsBuilder
from mysql.connector import Error
from mysql.connector import IntegrityError
import toml

# Function to create a connection to MySQL
def create_connection():
    try:
        connection = mysql.connector.connect(
            host=st.secrets["database"]["host"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            database=st.secrets["database"]["database"],
            port=st.secrets["database"]["port"],
        )
        if connection.is_connected():
            return connection
    except Error as e:
        st.error(f"Error: {e}")
        return None

# Login Function (for both admin and employee)
def login():
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        return  # Skip the login interface if already logged in


    st.image("img.png", width=200)
    st.title("Login")

    # Get username and password from user
    username = st.text_input("Username", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")

    # Check if login button is pressed
    if st.button("Login", key="login_button"):
        conn = create_connection()
        cursor = conn.cursor()

        # First check for Admin credentials
        cursor.execute("SELECT * FROM admin WHERE admin_username = %s AND admin_password = %s", (username, password))
        result = cursor.fetchone()

        if result:
            # Admin login successful
            st.session_state.logged_in = True
            st.session_state.username = username  # Set session state for username
            st.session_state.role = "admin"  # Set role as admin
            st.session_state.department = None  # Admin is not tied to a department

            st.success(f"Welcome Admin {username}, you are logged in!")
            conn.close()
            st.rerun()  # Force the page to rerun to show the admin dashboard
        else:
            # If Admin login fails, check employee credentials
            cursor.execute("SELECT * FROM employee WHERE username = %s AND password = %s", (username, password))
            result = cursor.fetchone()

            if result:
                # Employee login successful
                st.session_state.logged_in = True
                st.session_state.username = username  # Set session state for username
                st.session_state.role = "employee"
                st.session_state.department = result[3]  # Fetch the department from the employee record
                st.session_state.dob = result[4]  # Fetch the DOB from employee record

                st.success(f"Welcome {username}, you are logged in!")
                conn.close()
                st.rerun()  # Force the page to rerun to show the employee dashboard
            else:
                st.error("Invalid username or password!")

        conn.close()

# Admin Dashboard: Add or Remove Employee and Fetch Predictions
def admin_dashboard():
    st.title("Admin Dashboard")

    # 1. Add Employee
    st.header("Add Employee")
    emp_username = st.text_input("Username", key="add_emp_username_unique")
    # emp_password = st.text_input("Password", key="add_emp_password_unique")

    emp_dob = st.date_input(
        "Date of Birth",
        value=date(2000, 1, 1),  # Default date (e.g., January 1, 2000)
        min_value=date(1850, 1, 1),  # Minimum date (e.g., January 1, 1850)
        max_value=date.today(),  # Maximum date (e.g., today's date)
        key="add_emp_dob_unique"
    )
    emp_department = st.selectbox("Department", ["Sales", "Operations", "Credit", "Admin","Leadership"], key="add_emp_department_unique")

    # if st.button("Add Employee", key="add_employee_button_unique"):
    #
    #     if emp_username and emp_dob:
    #
    #         try:
    #         # Password is the combination of username and dob in the format 'usernameDDMMYYYY'
    #            password = emp_username + str(emp_dob.strftime("%d%m%Y"))
    #            conn = create_connection()
    #         cursor = conn.cursor()
    #         cursor.execute("INSERT INTO employee (username, password, department, dob) VALUES (%s, %s, %s, %s)",
    #                        (emp_username, password, emp_department, emp_dob))
    #         conn.commit()
    #         st.success(f"Employee {emp_username} added successfully!")
    #         conn.close()
    #
    #     else:
    #         st.error("All fields are required!")

    if st.button("Add Employee", key="add_employee_button_unique"):
        if emp_username and emp_dob:
            try:
                # Password is the combination of username and dob in the format 'usernameDDMMYYYY'
                password = emp_username + str(emp_dob.strftime("%d%m%Y"))
                conn = create_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO employee (username, password, department, dob) VALUES (%s, %s, %s, %s)",
                    (emp_username, password, emp_department, emp_dob)
                )
                conn.commit()
                st.success(f"Employee {emp_username} added successfully!")

            except IntegrityError as e:
                # Check if the error is due to duplicate entry (MySQL error code 1062)
                if e.errno == 1062:
                    st.error(f"Username '{emp_username}' is already taken. Please choose a different one.")
                else:
                    st.error("An error occurred while adding the employee. Please try again.")

            finally:
                # Close the connection
                conn.close()
        else:
            st.error("All fields are required!")

    # 2. Remove Employee (based on username and dob)
    st.header("Remove Employee")
    remove_username = st.text_input("Enter Username of Employee to Remove", key="remove_emp_username_unique")
    remove_dob = st.date_input(
        "Date of Birth",
        value=date(2000, 1, 1),  # Default date (e.g., January 1, 2000)
        min_value=date(1850, 1, 1),  # Minimum date (e.g., January 1, 1850)
        max_value=date.today(),  # Maximum date (e.g., today's date)
        key="remove_emp_dob_unique"
    )



    if st.button("Remove Employee", key="remove_employee_button_unique"):
        if remove_username and remove_dob:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employee WHERE username = %s AND dob = %s", (remove_username, remove_dob))
            conn.commit()
            if cursor.rowcount > 0:
                st.success(f"Employee {remove_username} removed successfully!")
            else:
                st.error("No matching employee found with the provided username and date of birth.")
            conn.close()
        else:
            st.error("Both username and date of birth are required!")

    # 3. Fetch All Employee Data and Download as CSV
    st.header("Fetch Employee Data and Download CSV")

    if st.button("Fetch Employee Data", key="fetch_employee_data_button_unique"):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employee")
        data = cursor.fetchall()

        if data:
            # Convert data to DataFrame
            df = pd.DataFrame(data, columns=["ID", "Username", "Password", "Department", "DOB"])
            # Convert DataFrame to CSV
            csv_data = df.to_csv(index=False)
            # Create a downloadable link for the CSV file
            st.download_button(
                label="Download Employee Data CSV",
                data=csv_data,
                file_name="employee_data.csv",
                mime="text/csv"
            )
            st.success("Employee data fetched successfully and ready for download.")
        else:
            st.error("No data found.")
        conn.close()

    # 4. Button for Admin to Download Personality Predictions CSV
    st.header("Download General Personality Predictions CSV")

    if st.button("Download  Sales Predictions CSV"):
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                   SELECT username, dob, cognitive_skills, personality_traits, emotional_intelligence,leadership, adaptability,communication, problem_solving_and_decision_making, time_management,
                   initiative, integrity FROM general
               """)
            data = cursor.fetchall()

            if data:
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=["Username", "DOB", "cognitive_skills", "personality_traits",
                                                 "emotional_intelligence", "leadership", "adaptability","communication and interpersonal", "problem_solving_and_decision_making","time_management","initiative","integrity"])
                # Convert DataFrame to CSV
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="Download Predictions CSV",
                    data=csv_data,
                    file_name="Sales_predictions.csv",
                    mime="text/csv"
                )
                st.success("Predictions data ready for download.")
            else:
                st.error("No predictions found in the database.")
            conn.close()
        else:
            st.error("Database connection failed.")



    if st.button("Download  Operation Predictions CSV"):
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                               SELECT username, dob, cognitive_skills, personality_traits, emotional_intelligence,leadership, adaptability,communication, problem_solving_and_decision_making, time_management,
                               initiative, integrity FROM general1
                           """)
            data = cursor.fetchall()

            if data:
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=["Username", "DOB", "cognitive_skills", "personality_traits",
                                                 "emotional_intelligence", "leadership", "adaptability",
                                                 "communication and interpersonal",
                                                 "problem_solving_and_decision_making", "time_management", "initiative",
                                                 "integrity"])
                # Convert DataFrame to CSV
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="Download Predictions CSV",
                    data=csv_data,
                    file_name="operaation_predictions.csv",
                    mime="text/csv"
                )
                st.success("Predictions data ready for download.")
            else:
                st.error("No predictions found in the database.")
            conn.close()
        else:
            st.error("Database connection failed.")
    if st.button("Download  Credit Predictions CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(""" SELECT username, dob, cognitive_skills, personality_traits, emotional_intelligence,leadership, adaptability,communication, problem_solving_and_decision_making, time_management,
                                               initiative, integrity FROM general1
                                           """)

                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "cognitive_skills", "personality_traits",
                                                     "emotional_intelligence", "leadership", "adaptability",
                                                     "communication and interpersonal",
                                                     "problem_solving_and_decision_making", "time_management",
                                                     "initiative",
                                                     "integrity"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download Predictions CSV",
                        data=csv_data,
                        file_name="credit_predictions.csv",
                        mime="text/csv"
                    )
                    st.success("Predictions data ready for download.")
                else:
                    st.error("No predictions found in the database.")
                conn.close()
            else:
                st.error("Database connection failed.")
    if st.button("Download  Leadership Predictions CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(""" SELECT username, dob, cognitive_skills, personality_traits, emotional_intelligence,leadership, adaptability,communication, problem_solving_and_decision_making, time_management,
                                                               initiative, integrity FROM general1
                                                           """)
                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "cognitive_skills", "personality_traits",
                                                     "emotional_intelligence", "leadership", "adaptability",
                                                     "communication and interpersonal",
                                                     "problem_solving_and_decision_making", "time_management",
                                                     "initiative",
                                                     "integrity"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download Leadership Predictions CSV",
                        data=csv_data,
                        file_name="leadership_predictions.csv",
                        mime="text/csv"
                    )
                    st.success("Leadership predictions ready for download.")
                else:
                    st.error("No leadership predictions found in the database.")
                conn.close()


    # Button to start the Sales Quiz setup
    st.title('Select department questions')
    department = st.selectbox(
        "Select Department",
        options=["None", "Sales", "Leadership", "Credit", "Operations",'General questions'],  # Default is blank (null)
        index=0  # Default selection is empty
    )

    if department == "Sales":  # Only display if the department is "Sales"
        # If the user selects "Sales", call the function to add questions for Sales department
        # clear_all_records()
        add_multiple_questions()
    elif department=='Operations':
        # clear_all_records1()
        add_multiple_questions1()
    elif department=='Credit':
        # clear_all_records2()
        add_multiple_questions2()
    elif department=='Leadership':
        # clear_all_records3()

        add_multiple_questions3()
    elif department=='General questions':
        add_general_question()

       # Show a message if another department is selected


        # Call the function to fetch and allow download of the prediction
    st.title('Download the quiz results')
    if st.button("Download  sales quiz CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, dob, customer_relationship_management, communication_skill, networking, persuasion, market_understanding
                    FROM response
                """)

                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "customer_relationship_management", "communication_skill",
                                                     "networking", "persuasion", "market_understanding"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download sales quiz CSV",
                        data=csv_data,
                        file_name="sales_quiz.csv",
                        mime="text/csv"
                    )
                    st.success("Sales quiz ready for download.")
                else:
                    st.error("No Sales quiz found in the database.")
                conn.close()
    if st.button("Download  Operation quiz CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, dob, Documentation_and_Record_Keeping, Process_Efficiency,Compliance_Knowledge
                    FROM response1
                """)

                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "Documentation and Record_Keeping", "Process Efficiency",
                                                     "Compliance Knowledge"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download operation quiz CSV",
                        data=csv_data,
                        file_name="operation_quiz.csv",
                        mime="text/csv"
                    )
                    st.success("operation quiz ready for download.")
                else:
                    st.error("No operation quiz found in the database.")
                conn.close()
    if st.button("Download  Credit quiz CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, dob, Analytical_Skills,Attention_to_Detail,Risk_Assessment,Knowledge_of_Lending_Principles
                    FROM response2
                """)

                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "Analytical Skills", " Attention to Detail","Risk Assessment",
                                                     "Knowledge of Lending Principles"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download credit quiz CSV",
                        data=csv_data,
                        file_name="credit_quiz.csv",
                        mime="text/csv"
                    )
                    st.success("credit quiz ready for download.")
                else:
                    st.error("No credit quiz found in the database.")
                conn.close()
    if st.button("Download  Leadership quiz CSV"):
            conn = create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, dob,Leadership,Communication,Strategic_Thinking,Emotional_Intelligence,Coaching,Problem_Solving,Collaboration
                     FROM response3
                """)

                data = cursor.fetchall()

                if data:
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=["Username", "DOB", "Leadership", "Communication",
                                                     "Strategic Thinking", "Emotional Intelligence", "Coaching","Problem Solving","Collaboration"])
                    # Convert DataFrame to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download leadership quiz CSV",
                        data=csv_data,
                        file_name="leadership_quiz.csv",
                        mime="text/csv"
                    )
                    st.success("leadership quiz ready for download.")
                else:
                    st.error("leadership quiz found in the database.")
                conn.close()
    st.title('Clear quiz records')
    st.write('Reset all sales record')
    if st.button('clear Sales'):
        clearsales()
    st.write('Reset all Operation records')
    if st.button('Clear Operation'):
         clearOperation()
    st.write('Reset all  Credit Records')
    if st.button('Clear Credit'):
        clearCredit()

    st.write('Reset all Leadership Records')
    if st.button('Clear Leadership'):
        clearleadership()


    st.title('Clear General test records')
    st.write('Reset all sales record')
    if st.button('clear Sales Prediction'):
        clearS()
    st.write('Reset all Operation records')
    if st.button('Clear Operation Predictions'):
        clearO()
    st.write('Reset all  Credit Records')
    if st.button('Clear Credit Predictions'):
        clearC()

    st.write('Reset all Leadership Records')
    if st.button('Clear Leadership  Predictions'):
        clearL()

    st.title('Delete All the Employee')
    if st.button('Delete all Employee'):
        clearE()
    st.title('clear Questions')
    st.write('Reset all sales Questions')
    if st.button('clear Sales Questions'):
        clear_all_records()
    st.write('Reset all Operation Questions')
    if st.button('clear Operation Questions'):
        clear_all_records1()
    st.write('Reset all Credit Questions')
    if st.button('clear Credit Questions'):
        clear_all_records2()
    st.write('Reset all LeaderShip Questions')
    if st.button('clear Leadership Questions'):
        clear_all_records3()
    st.write('Reset all General Questions')
    if st.button('clear General Questions'):
        clear_all_records4()




    # 5. Logout Button for Admin
    if st.button("Logout", key="admin_logout_button_unique"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.department = ""
        st.rerun()


# Fetch Predictions for Admin Download
def fetch_predictions_for_admin():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, dob, operational_skills, customer_centric_skills, flexibility, team_collaboration, initiative, cluster FROM predictions")
    data = cursor.fetchall()

    if data:
        # Convert data to DataFrame
        df = pd.DataFrame(data, columns=["Username", "DOB", "Operational Skills", "Customer-Centric Skills", "Flexibility", "Team Collaboration", "Initiative", "Cluster"])
        # Convert DataFrame to CSV
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Download Predictions CSV",
            data=csv_data,
            file_name="personality_predictions.csv",
            mime="text/csv"
        )
        st.success("Personality predictions ready for download.")
    else:
        st.error("No predictions found.")

    conn.close()


# Main Function: Control the flow of the application
def main():
    # Ensure session state is initialized properly
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.department = ""

    # Show login page if not logged in
    if not st.session_state.logged_in:
        login()  # Show the login page if the user is not logged in
    else:
        if st.session_state.role == "admin":
            admin_dashboard()  # Show Admin Dashboard if Admin is logged in
        else:
            employee_dashboard(st.session_state.department)


# Employee Dashboard: Display department-specific page
def employee_dashboard(department):
    st.title(f"Welcome to {department} Department")

    if department == 'Sales':
        st.subheader("Sales Department")
        st.write("Welcome to the Sales Department! Here are your tasks and goals.")
        # personality_prediction()
        # display_questions_with_labels()
        st.title('Sales department test')
        st.write('select which test do you want to give')
        check = st.selectbox(
            "Select Department",
            options=["None", "prediction","quiz"],  # Default is blank (null)
            index=0  # Default selection is empty
        )
        if check=='prediction':
            display_general()
        elif  check=='quiz' :
            display_questions_with_labels()


    elif department == 'Operations':
        st.subheader("Operations Department")
        st.write("Welcome to the Operations Department! Here are your operations-related tasks.")
        # personality_prediction1
        check = st.selectbox(
            "Select Department",
            options=["None", "prediction", "quiz"],  # Default is blank (null)
            index=0  # Default selection is empty
        )

        if check=='prediction':
            display_general1()
        elif check=='quiz' :
            display_questions_with_labels1()
    elif department == 'Credit':
        st.subheader("Credit Department")
        st.write("Welcome to the Credit Department! Here are your credit-related tasks.")
        # personality_prediction2()
        check = st.selectbox(
            "Select Department",
            options=["None", "prediction", "quiz"],  # Default is blank (null)
            index=0  # Default selection is empty
        )
        if check=='prediction':
            display_general2()
        elif check=='quiz' :
            display_questions_with_labels2()
    elif department == 'Leadership':
        st.subheader("Leadership Department")
        st.write("Welcome to the Leadership Department! Here you can review strategy tasks and team insights.")
        check = st.selectbox(
            "Select Department",
            options=["None", "prediction", "quiz"],  # Default is blank (null)
            index=0  # Default selection is empty
        )
        if check=='prediction':
            display_general3()   #---------------------
        elif check=='quiz' :
            display_questions_with_labels3()

        # personality_prediction3()
    elif department == 'Admin':
        st.subheader("Admin Department")
        st.write("Welcome to the Admin Department! Here you can manage the company's operations.")
        admin_dashboard()  # Admin dashboard handles the logout button
    else:
        st.error("Invalid department!")





    # Ensure that the logout button only appears for non-admin departments
    if department != 'Admin' and st.button("Logout", key="employee_logout_button_unique"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.department = ""
        st.rerun()  # Force page reload to


def add_multiple_questions():
    st.title("Admin Dashboard - Add Questions and Scores")

    for i in range(1, 16):  # Loop for 15 questions
        # Create a form for each question
        with st.form(key=f"question_form_{i}"):
            st.subheader(f"Add Question {i}")

            # Input fields for question and options
            question_text = st.text_area(
                f"Enter Question {i}",
                value=f"Sample Question {i} (In English and Hindi)"
            )
            option_a = st.text_input(f"Enter Option A for Question {i}")
            option_b = st.text_input(f"Enter Option B for Question {i}")
            option_c = st.text_input(f"Enter Option C for Question {i}")
            option_d = st.text_input(f"Enter Option D for Question {i}")
            option_a_score = st.number_input(f"Score for Option A (Question {i})", min_value=0)
            option_b_score = st.number_input(f"Score for Option B (Question {i})", min_value=0)
            option_c_score = st.number_input(f"Score for Option C (Question {i})", min_value=0)
            option_d_score = st.number_input(f"Score for Option D (Question {i})", min_value=0)

            submit_button = st.form_submit_button(label=f"Add Question {i}")

            if submit_button:
                if question_text and option_a and option_b and option_c and option_d:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()

                        # Insert record (auto-increment `id`)
                        cursor.execute(''' 
                            INSERT INTO questions_scores (
                                question_id, question_text, option_a, option_b, option_c, option_d, 
                                option_a_score, option_b_score, option_c_score, option_d_score
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ''', (f"{i}.1", question_text, option_a, option_b, option_c, option_d,
                              option_a_score, option_b_score, option_c_score, option_d_score))
                        conn.commit()
                        conn.close()

                        st.success(f"Question {i} added successfully.")
                    except Exception as e:
                        st.error(f"Error occurred: {e}")
                else:
                    st.error("All fields must be filled out.")

        st.write("---")








# Function to add multiple questions to the database
def display_questions_with_labels():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "Customer Relationship Management",
        "Communication",
        "Networking",
        "Persuasion",
        "Market Understanding"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM questions_scores")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize responses for each category

    # If the user has already submitted, show the results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        # Display results and "Retake" button
        st.subheader("Results")
        calculate_percentages(user_responses, labels)

        # Retake option
        if st.button("Take the Quiz"):
            # Reset responses and submission state
            st.session_state.submitted = False
            st.rerun()  # Reload the page to retake the quiz
    else:
        # Display quiz questions if not submitted
        if rows:
            # Split questions into 5 categories, 3 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 3 + 1} to {(i + 1) * 3})")

                # Displaying 3 questions per label
                category_questions = rows[i * 3: (i + 1) * 3]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    # Radio button with no default index set
                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]  # Extract option letter (A, B, C, D)
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert the calculated scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO response (username, dob, customer_relationship_management, communication_skill, 
                        networking, persuasion, market_understanding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        username,
                        dob,
                        user_responses["Customer Relationship Management"] / 30 * 100,
                        user_responses["Communication"] / 30 * 100,
                        user_responses["Networking"] / 30 * 100,
                        user_responses["Persuasion"] / 30 * 100,
                        user_responses["Market Understanding"] / 30 * 100
                    ))

                    conn.commit()
                    conn.close()

                    # Display submission confirmation message
                    st.success("Your responses have been successfully submitted!")

                    # Set submitted state to True
                    st.session_state.submitted = True

                    # Hide quiz questions after submission
                    st.rerun()  # Reload the page to hide the quiz

                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")

def calculate_percentages(user_responses, labels):
    for label in labels:
        total_score = user_responses[label]
        percentage = (total_score / 30) * 100



def clear_all_records():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions_scores;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

#     ----------------------------
def add_multiple_questions1():
    st.title("Admin Dashboard - Add Questions and Scores")

    for i in range(1, 10):  # Loop for 15 questions
        # Create a form for each question
        with st.form(key=f"question_form_{i}"):
            st.subheader(f"Add Question {i}")

            # Input fields for question and options
            question_text = st.text_area(
                f"Enter Question {i}",
                value=f"Sample Question {i} (In English and Hindi)"
            )
            option_a = st.text_input(f"Enter Option A for Question {i}")
            option_b = st.text_input(f"Enter Option B for Question {i}")
            option_c = st.text_input(f"Enter Option C for Question {i}")
            option_d = st.text_input(f"Enter Option D for Question {i}")
            option_a_score = st.number_input(f"Score for Option A (Question {i})", min_value=0)
            option_b_score = st.number_input(f"Score for Option B (Question {i})", min_value=0)
            option_c_score = st.number_input(f"Score for Option C (Question {i})", min_value=0)
            option_d_score = st.number_input(f"Score for Option D (Question {i})", min_value=0)

            submit_button = st.form_submit_button(label=f"Add Question {i}")

            if submit_button:
                if question_text and option_a and option_b and option_c and option_d:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()

                        # Insert record (auto-increment `id`)
                        cursor.execute(''' 
                            INSERT INTO questions_scores1 (
                                question_id, question_text, option_a, option_b, option_c, option_d, 
                                option_a_score, option_b_score, option_c_score, option_d_score
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ''', (f"{i}.1", question_text, option_a, option_b, option_c, option_d,
                              option_a_score, option_b_score, option_c_score, option_d_score))
                        conn.commit()
                        conn.close()

                        st.success(f"Question {i} added successfully.")
                    except Exception as e:
                        st.error(f"Error occurred: {e}")
                else:
                    st.error("All fields must be filled out.")

        st.write("---")

#-----------------------------------------------------------------------------------------
def display_questions_with_labels1():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "Documentation_and_Record_Keeping",
        "Process_Efficiency",
        "Compliance_Knowledge"


    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM questions_scores1")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize responses for each category

    # If the user has already submitted, show the results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        # Display results and "Retake" button
        st.subheader("Results")
        calculate_percentages(user_responses, labels)

        # Retake option
        if st.button("Take the Quiz"):
            # Reset responses and submission state
            st.session_state.submitted = False
            st.rerun()  # Reload the page to retake the quiz
    else:
        # Display quiz questions if not submitted
        if rows:
            # Split questions into 5 categories, 3 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 3 + 1} to {(i + 1) * 3})")

                # Displaying 3 questions per label
                category_questions = rows[i * 3: (i + 1) * 3]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    # Radio button with no default index set
                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]  # Extract option letter (A, B, C, D)
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert the calculated scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO response1 (username, dob,Documentation_and_Record_Keeping,Process_Efficiency, 
                        Compliance_Knowledge)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        username,
                        dob,
                        user_responses["Documentation_and_Record_Keeping"] / 30 * 100,
                        user_responses["Process_Efficiency"] / 30 * 100,
                        user_responses["Compliance_Knowledge"] / 30 * 100,

                    ))

                    conn.commit()
                    conn.close()

                    # Display submission confirmation message
                    st.success("Your responses have been successfully submitted!")

                    # Set submitted state to True
                    st.session_state.submitted = True

                    # Hide quiz questions after submission
                    st.rerun()  # Reload the page to hide the quiz

                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")

def clear_all_records1():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions_scores1;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

#     ---------------------------------------------------------------------------------------------------------
def add_multiple_questions2():
    st.title("Admin Dashboard - Add Questions and Scores")

    for i in range(1, 13):  # Loop for 15 questions
        # Create a form for each question
        with st.form(key=f"question_form_{i}"):
            st.subheader(f"Add Question {i}")

            # Input fields for question and options
            question_text = st.text_area(
                f"Enter Question {i}",
                value=f"Sample Question {i} (In English and Hindi)"
            )
            option_a = st.text_input(f"Enter Option A for Question {i}")
            option_b = st.text_input(f"Enter Option B for Question {i}")
            option_c = st.text_input(f"Enter Option C for Question {i}")
            option_d = st.text_input(f"Enter Option D for Question {i}")
            option_a_score = st.number_input(f"Score for Option A (Question {i})", min_value=0)
            option_b_score = st.number_input(f"Score for Option B (Question {i})", min_value=0)
            option_c_score = st.number_input(f"Score for Option C (Question {i})", min_value=0)
            option_d_score = st.number_input(f"Score for Option D (Question {i})", min_value=0)

            submit_button = st.form_submit_button(label=f"Add Question {i}")

            if submit_button:
                if question_text and option_a and option_b and option_c and option_d:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()

                        # Insert record (auto-increment `id`)
                        cursor.execute(''' 
                            INSERT INTO questions_scores2 (
                                question_id, question_text, option_a, option_b, option_c, option_d, 
                                option_a_score, option_b_score, option_c_score, option_d_score
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ''', (f"{i}.1", question_text, option_a, option_b, option_c, option_d,
                              option_a_score, option_b_score, option_c_score, option_d_score))
                        conn.commit()
                        conn.close()

                        st.success(f"Question {i} added successfully.")
                    except Exception as e:
                        st.error(f"Error occurred: {e}")
                else:
                    st.error("All fields must be filled out.")

        st.write("---")


#         ----------------------------------------------------------------------------------------------------
def display_questions_with_labels2():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "Analytical_Skills",
        "Attention_to_Detail",
        "Risk_Assessment",
        "Knowledge_of_Lending_Principles",

    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM questions_scores2")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize responses for each category

    # If the user has already submitted, show the results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        # Display results and "Retake" button
        st.subheader("Results")
        calculate_percentages(user_responses, labels)

        # Retake option
        if st.button("Take the Quiz"):
            # Reset responses and submission state
            st.session_state.submitted = False
            st.rerun()  # Reload the page to retake the quiz
    else:
        # Display quiz questions if not submitted
        if rows:
            # Split questions into 5 categories, 3 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 3 + 1} to {(i + 1) * 3})")

                # Displaying 3 questions per label
                category_questions = rows[i * 3: (i + 1) * 3]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    # Radio button with no default index set
                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]  # Extract option letter (A, B, C, D)
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert the calculated scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO response2 (username, dob, Analytical_Skills,Attention_to_Detail, 
                        Risk_Assessment,Knowledge_of_Lending_Principles)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        username,
                        dob,
                        user_responses["Analytical_Skills"] / 30 * 100,
                        user_responses["Attention_to_Detail"] / 30 * 100,
                        user_responses["Risk_Assessment"] / 30 *100,
                        user_responses["Knowledge_of_Lending_Principles"] / 30 * 100,

                    ))

                    conn.commit()
                    conn.close()

                    # Display submission confirmation message
                    st.success("Your responses have been successfully submitted!")

                    # Set submitted state to True
                    st.session_state.submitted = True

                    # Hide quiz questions after submission
                    st.rerun()  # Reload the page to hide the quiz

                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")
#             -----------------
def clear_all_records2():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions_scores2;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")
#     ----------------------------------------------------------------------------
def add_multiple_questions3():
    st.title("Admin Dashboard - Add Questions and Scores")

    for i in range(1, 15):  # Loop for 15 questions
        # Create a form for each question
        with st.form(key=f"question_form_{i}"):
            st.subheader(f"Add Question {i}")

            # Input fields for question and options
            question_text = st.text_area(
                f"Enter Question {i}",
                value=f"Sample Question {i} (In English and Hindi)"
            )
            option_a = st.text_input(f"Enter Option A for Question {i}")
            option_b = st.text_input(f"Enter Option B for Question {i}")
            option_c = st.text_input(f"Enter Option C for Question {i}")
            option_d = st.text_input(f"Enter Option D for Question {i}")
            option_a_score = st.number_input(f"Score for Option A (Question {i})", min_value=0)
            option_b_score = st.number_input(f"Score for Option B (Question {i})", min_value=0)
            option_c_score = st.number_input(f"Score for Option C (Question {i})", min_value=0)
            option_d_score = st.number_input(f"Score for Option D (Question {i})", min_value=0)

            submit_button = st.form_submit_button(label=f"Add Question {i}")

            if submit_button:
                if question_text and option_a and option_b and option_c and option_d:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()

                        # Insert record (auto-increment `id`)
                        cursor.execute(''' 
                            INSERT INTO questions_scores3 (
                                question_id, question_text, option_a, option_b, option_c, option_d, 
                                option_a_score, option_b_score, option_c_score, option_d_score
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ''', (f"{i}.1", question_text, option_a, option_b, option_c, option_d,
                              option_a_score, option_b_score, option_c_score, option_d_score))
                        conn.commit()
                        conn.close()

                        st.success(f"Question {i} added successfully.")
                    except Exception as e:
                        st.error(f"Error occurred: {e}")
                else:
                    st.error("All fields must be filled out.")

        st.write("---")
#         ----------------------------------------------------------------------------------------------------
def display_questions_with_labels3():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "Leadership",
        "Communication",
        "Strategic_Thinking",
        "Emotional_Intelligence",
        "Coaching",
        "Problem_Solving",
        "Collaboration"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM questions_scores3")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize responses for each category

    # If the user has already submitted, show the results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        # Display results and "Retake" button
        st.subheader("Results")
        calculate_percentages(user_responses, labels)

        # Retake option
        if st.button("Take the Quiz"):
            # Reset responses and submission state
            st.session_state.submitted = False
            st.rerun()  # Reload the page to retake the quiz
    else:
        # Display quiz questions if not submitted
        if rows:
            # Split questions into 5 categories, 3 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 2 + 1} to {(i + 1) * 2})")

                # Displaying 3 questions per label
                category_questions = rows[i * 2: (i + 1) * 2]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    # Radio button with no default index set
                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]  # Extract option letter (A, B, C, D)
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert the calculated scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO response3 (username, dob,Leadership,Communication,Strategic_Thinking,Emotional_Intelligence,
                        Coaching,Problem_Solving,Collaboration)
                        VALUES (%s, %s, %s, %s, %s, %s, %s,%s,%s)
                    """, (
                        username,
                        dob,
                        user_responses["Leadership"] / 20 * 100,
                        user_responses["Communication"] /20 * 100,
                        user_responses["Strategic_Thinking"] / 20 * 100,
                        user_responses["Emotional_Intelligence"] /20 * 100,
                        user_responses["Coaching"] / 20 * 100,
                        user_responses["Problem_Solving"] / 20 * 100,
                        user_responses["Collaboration"] /20 * 100
                    ))

                    conn.commit()
                    conn.close()

                    # Display submission confirmation message
                    st.success("Your responses have been successfully submitted!")

                    # Set submitted state to True
                    st.session_state.submitted = True

                    # Hide quiz questions after submission
                    st.rerun()  # Reload the page to hide the quiz

                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")
#             -----------------
def clear_all_records3():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions_scores3;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")


# -----------------------------------clear------------------------------------
def clearsales():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM response;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearOperation():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM response1;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearCredit():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM response2;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearleadership():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM response3;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")


def add_general_question():
    st.title("Admin Dashboard - Add Questions and Scores")

    for i in range(1, 21):  # Loop for 15 questions
        # Create a form for each question
        with st.form(key=f"question_form_{i}"):
            st.subheader(f"Add Question {i}")

            # Input fields for question and options
            question_text = st.text_area(
                f"Enter Question {i}",
                value=f"Sample Question {i} (In English and Hindi)"
            )
            option_a = st.text_input(f"Enter Option A for Question {i}")
            option_b = st.text_input(f"Enter Option B for Question {i}")
            option_c = st.text_input(f"Enter Option C for Question {i}")
            option_d = st.text_input(f"Enter Option D for Question {i}")
            option_a_score = st.number_input(f"Score for Option A (Question {i})", min_value=0)
            option_b_score = st.number_input(f"Score for Option B (Question {i})", min_value=0)
            option_c_score = st.number_input(f"Score for Option C (Question {i})", min_value=0)
            option_d_score = st.number_input(f"Score for Option D (Question {i})", min_value=0)

            submit_button = st.form_submit_button(label=f"Add Question {i}")

            if submit_button:
                if question_text and option_a and option_b and option_c and option_d:
                    try:
                        conn = create_connection()
                        cursor = conn.cursor()

                        # Insert record (auto-increment `id`)
                        cursor.execute(''' 
                            INSERT INTO common (
                                question_id, question_text, option_a, option_b, option_c, option_d, 
                                option_a_score, option_b_score, option_c_score, option_d_score
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                        ''', (f"{i}.1", question_text, option_a, option_b, option_c, option_d,
                              option_a_score, option_b_score, option_c_score, option_d_score))
                        conn.commit()
                        conn.close()

                        st.success(f"Question {i} added successfully.")
                    except Exception as e:
                        st.error(f"Error occurred: {e}")
                else:
                    st.error("All fields must be filled out.")

        st.write("---")


def display_general():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "cognitive_skills",
        "personality_traits",
        "emotional_intelligence",
        "leadership",
        "adaptability",
        "communication",
        "problem_solving_and_decision_making",
        "time_management",
        "initiative",
        "integrity"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM common")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize scores for each category

    # If the user has already submitted, show results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        st.subheader("Results")
        # general_percentages(user_responses, labels)


        # Retake option
        if st.button("take Quiz"):
            st.session_state.submitted = False
            st.rerun()
    else:
        if rows:
            # Display 2 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 2 + 1} to {(i + 1) * 2})")

                # Get 2 questions per category
                category_questions = rows[i * 2: (i + 1) * 2]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO general (username, dob, cognitive_skills, personality_traits, emotional_intelligence, 
                                             leadership, adaptability,communication, problem_solving_and_decision_making, time_management , 
                                             initiative, integrity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """, (
                        username,
                        dob,
                        user_responses["cognitive_skills"] / 20 * 100,  # Calculating percentage
                        user_responses["personality_traits"] / 20 * 100,
                        user_responses["emotional_intelligence"] / 20 * 100,
                        user_responses["leadership"] / 20 * 100,
                        user_responses["adaptability"] / 20 * 100,
                        user_responses["communication"] / 20 * 100,
                        user_responses["problem_solving_and_decision_making"] / 20 * 100,
                        user_responses["time_management"] / 20 * 100,
                        user_responses["initiative"] / 20 * 100,
                        user_responses["integrity"] / 20 * 100
                    ))
                    conn.commit()
                    conn.close()

                    st.success("Your responses have been successfully submitted! 🎉")

                    st.session_state.submitted = True

                    st.rerun()
                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")




def display_general1():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "cognitive_skills",
        "personality_traits",
        "emotional_intelligence",
        "leadership",
        "adaptability",
        "communication",
        "problem_solving_and_decision_making",
        "time_management",
        "initiative",
        "integrity"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM common")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize scores for each category

    # If the user has already submitted, show results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        st.subheader("Results")
        # general_percentages(user_responses, labels)


        # Retake option
        if st.button("take Quiz"):
            st.session_state.submitted = False
            st.rerun()
    else:
        if rows:
            # Display 2 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 2 + 1} to {(i + 1) * 2})")

                # Get 2 questions per category
                category_questions = rows[i * 2: (i + 1) * 2]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO general1 (username, dob, cognitive_skills, personality_traits, emotional_intelligence, 
                                             leadership, adaptability,communication, problem_solving_and_decision_making, time_management , 
                                             initiative, integrity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """, (
                        username,
                        dob,
                        user_responses["cognitive_skills"] / 20 * 100,  # Calculating percentage
                        user_responses["personality_traits"] / 20 * 100,
                        user_responses["emotional_intelligence"] / 20 * 100,
                        user_responses["leadership"] / 20 * 100,
                        user_responses["adaptability"] / 20 * 100,
                        user_responses["communication"] / 20 * 100,
                        user_responses["problem_solving_and_decision_making"] / 20 * 100,
                        user_responses["time_management"] / 20 * 100,
                        user_responses["initiative"] / 20 * 100,
                        user_responses["integrity"] / 20 * 100
                    ))

                    conn.commit()
                    conn.close()
                    # st.success("Your responses have been successfully submitted!")
                    st.success("Your responses have been successfully submitted! 🎉")
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")



def display_general2():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "cognitive_skills",
        "personality_traits",
        "emotional_intelligence",
        "leadership",
        "adaptability",
        "communication",
        "problem_solving_and_decision_making",
        "time_management",
        "initiative",
        "integrity"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM common")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize scores for each category

    # If the user has already submitted, show results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        st.subheader("Results")
        # general_percentages(user_responses, labels)


        # Retake option
        if st.button("take Quiz"):
            st.session_state.submitted = False
            st.rerun()
    else:
        if rows:
            # Display 2 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 2 + 1} to {(i + 1) * 2})")

                # Get 2 questions per category
                category_questions = rows[i * 2: (i + 1) * 2]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO general2 (username, dob, cognitive_skills, personality_traits, emotional_intelligence, 
                                             leadership, adaptability,communication, problem_solving_and_decision_making, time_management , 
                                             initiative, integrity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """, (
                        username,
                        dob,
                        user_responses["cognitive_skills"] / 20 * 100,  # Calculating percentage
                        user_responses["personality_traits"] / 20 * 100,
                        user_responses["emotional_intelligence"] / 20 * 100,
                        user_responses["leadership"] / 20 * 100,
                        user_responses["adaptability"] / 20 * 100,
                        user_responses["communication"] / 20 * 100,
                        user_responses["problem_solving_and_decision_making"] / 20 * 100,
                        user_responses["time_management"] / 20 * 100,
                        user_responses["initiative"] / 20 * 100,
                        user_responses["integrity"] / 20 * 100
                    ))

                    conn.commit()
                    conn.close()
                    # st.success("Your responses have been successfully submitted!")
                    st.success("Your responses have been successfully submitted! 🎉")
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")


def display_general3():
    st.title("Quiz Questions by Category")

    # Categories
    labels = [
        "cognitive_skills",
        "personality_traits",
        "emotional_intelligence",
        "leadership",
        "adaptability",
        "communication",
        "problem_solving_and_decision_making",
        "time_management",
        "initiative",
        "integrity"
    ]

    conn = create_connection()
    cursor = conn.cursor()

    # Fetching all questions from the database
    cursor.execute(
        "SELECT question_id, question_text, option_a, option_b, option_c, option_d, option_a_score, option_b_score, option_c_score, option_d_score FROM common")
    rows = cursor.fetchall()
    conn.close()

    user_responses = {label: 0 for label in labels}  # Initialize scores for each category

    # If the user has already submitted, show results and "Retake" button
    if 'submitted' in st.session_state and st.session_state.submitted:
        st.subheader("Results")
        # general_percentages(user_responses, labels)


        # Retake option
        if st.button("Take Quiz"):
            st.session_state.submitted = False
            st.rerun()
    else:
        if rows:
            # Display 2 questions per category
            for i, label in enumerate(labels):
                st.subheader(f"{label} (Questions {i * 2 + 1} to {(i + 1) * 2})")

                # Get 2 questions per category
                category_questions = rows[i * 2: (i + 1) * 2]
                for question in category_questions:
                    question_id, question_text, option_a, option_b, option_c, option_d, a_score, b_score, c_score, d_score = question
                    st.write(f"**{question_text}**")

                    selected_option = st.radio(
                        f"Select an option for {question_id}:",
                        [f"A) {option_a}", f"B) {option_b}", f"C) {option_c}", f"D) {option_d}"],
                        key=question_id,index=None
                    )

                    # Save the user's response and score
                    if selected_option:
                        selected_label = selected_option.split(') ')[0]
                        if selected_label == "A":
                            user_responses[label] += a_score
                        elif selected_label == "B":
                            user_responses[label] += b_score
                        elif selected_label == "C":
                            user_responses[label] += c_score
                        elif selected_label == "D":
                            user_responses[label] += d_score

            # Submit button to calculate percentages
            if st.button("Submit"):
                if 'username' in st.session_state and 'dob' in st.session_state:
                    username = st.session_state.username
                    dob = st.session_state.dob

                    conn = create_connection()
                    cursor = conn.cursor()

                    # Insert scores for each category into the response table
                    cursor.execute("""
                        INSERT INTO general3 (username, dob, cognitive_skills, personality_traits, emotional_intelligence,
                                             leadership, adaptability,communication, problem_solving_and_decision_making, time_management ,
                                             initiative, integrity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """, (
                        username,
                        dob,
                        user_responses["cognitive_skills"] / 20 * 100,  # Calculating percentage
                        user_responses["personality_traits"] / 20 * 100,
                        user_responses["emotional_intelligence"] / 20 * 100,
                        user_responses["leadership"] / 20 * 100,
                        user_responses["adaptability"] / 20 * 100,
                        user_responses["communication"] / 20 * 100,
                        user_responses["problem_solving_and_decision_making"] / 20 * 100,
                        user_responses["time_management"] / 20 * 100,
                        user_responses["initiative"] / 20 * 100,
                        user_responses["integrity"] / 20 * 100
                    ))

                    conn.commit()
                    conn.close()
                    # st.success("Your responses have been successfully submitted!")
                    st.success("Your responses have been successfully submitted! 🎉")
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Please log in first to submit responses.")
        else:
            st.warning("No questions available in the database.")


def clearS():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  general;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearO():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  general1;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")
def clearC():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  general2;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearL():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  general3;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clearE():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  employee;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")

def clear_all_records4():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM  common;")
    conn.commit()
    conn.close()
    st.success("All records have been cleared.")
if __name__ == '__main__':
    main()

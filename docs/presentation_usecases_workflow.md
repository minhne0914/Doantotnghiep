# Medic Project - Use Case And Workflow Diagrams

This document is prepared for the graduation presentation. Diagram labels are in English so they can be used directly in slides.

## 1. Overall Use Case Diagram

```mermaid
flowchart LR
    Patient["Patient"]
    Doctor["Doctor"]
    Admin["Administrator"]
    AI["AI Service"]
    Email["Email / Notification Service"]

    subgraph System["Medic Healthcare Web System"]
        UC1(("Register / Login"))
        UC2(("Manage Profile"))
        UC3(("Search Doctors"))
        UC4(("Filter by Specialty and Date"))
        UC5(("Book Appointment"))
        UC6(("View Appointment History"))
        UC7(("Cancel / Update Appointment"))
        UC8(("Doctor Dashboard"))
        UC9(("Manage Doctor Schedule"))
        UC10(("View Patient Appointments"))
        UC11(("Create / Update Medical Record"))
        UC12(("Admin Dashboard"))
        UC13(("Manage Users"))
        UC14(("Manage Doctor Profiles"))
        UC15(("Manage Appointments"))
        UC16(("View Statistics and Reports"))
        UC17(("AI Chatbot Consultation"))
        UC18(("AI Disease Screening"))
        UC19(("Multilingual Interface"))
    end

    Patient --> UC1
    Patient --> UC2
    Patient --> UC3
    Patient --> UC4
    Patient --> UC5
    Patient --> UC6
    Patient --> UC7
    Patient --> UC17
    Patient --> UC18
    Patient --> UC19

    Doctor --> UC1
    Doctor --> UC8
    Doctor --> UC9
    Doctor --> UC10
    Doctor --> UC11
    Doctor --> UC19

    Admin --> UC1
    Admin --> UC12
    Admin --> UC13
    Admin --> UC14
    Admin --> UC15
    Admin --> UC16
    Admin --> UC19

    UC17 --> AI
    UC18 --> AI
    UC5 --> Email
    UC7 --> Email
    UC15 --> Email
```

## 2. Detailed Use Case 1 - Authentication And Role Access

```mermaid
flowchart LR
    Guest["Guest / User"]

    subgraph Auth["Authentication Module"]
        A1(("Register Account"))
        A2(("Login"))
        A3(("Logout"))
        A4(("Validate Credentials"))
        A5(("Redirect by Role"))
        A6(("Access Protected Pages"))
    end

    Guest --> A1
    Guest --> A2
    A2 --> A4
    A4 --> A5
    A5 --> A6
    Guest --> A3
```

| Field | Description |
|---|---|
| Main actor | Guest, Patient, Doctor, Administrator |
| Goal | Allow users to securely access the correct area based on their role. |
| Precondition | The user has an account or can register a new account. |
| Main flow | User opens login page -> enters credentials -> system validates account -> system redirects to the correct dashboard. |
| Alternative flow | Invalid credentials -> system shows an error message and asks the user to try again. |
| Result | The user accesses only the pages allowed for their role. |

## 3. Detailed Use Case 2 - Search Doctors And Book Appointment

```mermaid
flowchart LR
    Patient["Patient"]

    subgraph Appointment["Appointment Booking Module"]
        B1(("Open Doctor List"))
        B2(("Search by Doctor Name"))
        B3(("Filter by Specialty"))
        B4(("Filter by Available Date"))
        B5(("View Doctor Detail"))
        B6(("Select Time Slot"))
        B7(("Submit Appointment"))
        B8(("Receive Confirmation"))
    end

    Patient --> B1
    B1 --> B2
    B1 --> B3
    B1 --> B4
    B2 --> B5
    B3 --> B5
    B4 --> B5
    B5 --> B6
    B6 --> B7
    B7 --> B8
```

| Field | Description |
|---|---|
| Main actor | Patient |
| Goal | Help patients find a suitable doctor and book an appointment. |
| Precondition | Doctor profiles and schedules already exist in the system. |
| Main flow | Patient opens doctor page -> searches or filters doctors -> selects a doctor -> chooses a time slot -> submits appointment form. |
| Alternative flow | No doctor matches the filters -> system shows an empty state and allows viewing all doctors. |
| Result | A new appointment request is created and stored in the database. |

## 4. Detailed Use Case 3 - Patient Appointment Management

```mermaid
flowchart LR
    Patient["Patient"]

    subgraph PatientAppointments["Patient Appointment Module"]
        C1(("View My Appointments"))
        C2(("Check Appointment Status"))
        C3(("View Doctor Information"))
        C4(("Update Appointment Request"))
        C5(("Cancel Appointment"))
        C6(("Receive Status Notification"))
    end

    Patient --> C1
    C1 --> C2
    C1 --> C3
    C2 --> C4
    C2 --> C5
    C4 --> C6
    C5 --> C6
```

| Field | Description |
|---|---|
| Main actor | Patient |
| Goal | Let patients track and manage their appointment requests. |
| Precondition | The patient is logged in and has at least one appointment. |
| Main flow | Patient opens appointment history -> checks status -> views doctor and schedule details. |
| Alternative flow | Patient cancels or requests an update before the allowed deadline. |
| Result | Appointment data is updated and the patient can follow the latest status. |

## 5. Detailed Use Case 4 - Doctor Schedule And Medical Record Management

```mermaid
flowchart LR
    Doctor["Doctor"]

    subgraph DoctorModule["Doctor Workspace"]
        D1(("Open Doctor Dashboard"))
        D2(("Create Available Schedule"))
        D3(("View Patient Appointments"))
        D4(("Approve / Reject Appointment"))
        D5(("Open Patient Detail"))
        D6(("Create / Update Medical Record"))
        D7(("Save Diagnosis and Treatment"))
    end

    Doctor --> D1
    D1 --> D2
    D1 --> D3
    D3 --> D4
    D3 --> D5
    D5 --> D6
    D6 --> D7
```

| Field | Description |
|---|---|
| Main actor | Doctor |
| Goal | Help doctors manage schedules, appointments, and patient medical data. |
| Precondition | The doctor is logged in and has a doctor profile. |
| Main flow | Doctor opens dashboard -> creates schedule -> reviews appointment list -> confirms patient visit -> updates medical record. |
| Alternative flow | Appointment is invalid or unavailable -> doctor rejects or asks for a different time. |
| Result | Doctor schedule and medical records are updated in the system. |

## 6. Detailed Use Case 5 - Admin System Management

```mermaid
flowchart LR
    Admin["Administrator"]

    subgraph AdminModule["Administration Module"]
        E1(("Open Admin Dashboard"))
        E2(("Manage Users"))
        E3(("Manage Doctor Profiles"))
        E4(("Manage Appointments"))
        E5(("Review Statistics"))
        E6(("Manage News / System Content"))
        E7(("Monitor System Data"))
    end

    Admin --> E1
    E1 --> E2
    E1 --> E3
    E1 --> E4
    E1 --> E5
    E1 --> E6
    E1 --> E7
```

| Field | Description |
|---|---|
| Main actor | Administrator |
| Goal | Control and maintain the main data of the healthcare system. |
| Precondition | The administrator is logged in with admin permission. |
| Main flow | Admin opens dashboard -> manages users, doctors, appointments, and system content -> reviews statistics. |
| Alternative flow | Invalid input -> system validates the form and shows errors. |
| Result | System data stays consistent and manageable. |

## 7. Detailed Use Case 6 - AI Assistant And AI Screening

```mermaid
flowchart LR
    Patient["Patient"]
    AI["AI / ML Service"]

    subgraph AIModule["AI Support Module"]
        F1(("Open AI Chatbox"))
        F2(("Ask Healthcare Question"))
        F3(("Retrieve System / Medical Context"))
        F4(("Generate AI Response"))
        F5(("Open AI Screening Tool"))
        F6(("Submit Health Data or Image"))
        F7(("Preprocess Input"))
        F8(("Run Prediction Model"))
        F9(("Show Screening Result"))
        F10(("Save AI History"))
    end

    Patient --> F1
    F1 --> F2
    F2 --> F3
    F3 --> F4
    F4 --> Patient

    Patient --> F5
    F5 --> F6
    F6 --> F7
    F7 --> F8
    F8 --> F9
    F9 --> F10

    F4 --> AI
    F8 --> AI
```

| Field | Description |
|---|---|
| Main actor | Patient |
| Supporting actor | AI / ML service |
| Goal | Provide quick healthcare support and preliminary screening. |
| Precondition | AI model or chatbot service is available. |
| Main flow | Patient asks a question or uploads data -> system processes input -> AI generates a response or prediction -> result is shown to the user. |
| Alternative flow | AI model is unavailable -> system shows a friendly fallback message. |
| Result | User receives AI-supported information, but the result is not a final medical diagnosis. |

## 8. Main System Workflow

```mermaid
flowchart TD
    Start([Start])
    Home["Open Home Page"]
    Auth{"Is user logged in?"}
    Login["Login / Register"]
    Role{"User role?"}

    PatientHome["Patient Area"]
    DoctorHome["Doctor Dashboard"]
    AdminHome["Admin Dashboard"]

    SearchDoctor["Search and Filter Doctors"]
    Book["Book Appointment"]
    Track["Track Appointment Status"]
    AIUse["Use AI Chatbot or Screening"]

    DoctorSchedule["Create / Manage Schedule"]
    DoctorAppointments["Review Appointments"]
    EMR["Update Medical Record"]

    ManageUsers["Manage Users and Doctors"]
    ManageAppointments["Manage Appointments"]
    Reports["View Statistics and Reports"]

    End([End])

    Start --> Home
    Home --> Auth
    Auth -- No --> Login
    Login --> Role
    Auth -- Yes --> Role

    Role -- Patient --> PatientHome
    Role -- Doctor --> DoctorHome
    Role -- Admin --> AdminHome

    PatientHome --> SearchDoctor
    SearchDoctor --> Book
    Book --> Track
    PatientHome --> AIUse
    Track --> End
    AIUse --> End

    DoctorHome --> DoctorSchedule
    DoctorHome --> DoctorAppointments
    DoctorAppointments --> EMR
    EMR --> End

    AdminHome --> ManageUsers
    AdminHome --> ManageAppointments
    AdminHome --> Reports
    ManageUsers --> End
    ManageAppointments --> End
    Reports --> End
```

## 9. Appointment Booking Workflow

```mermaid
sequenceDiagram
    actor Patient
    participant UI as Web Interface
    participant View as Django View
    participant DB as Database
    participant Notify as Notification Service
    participant Doctor

    Patient->>UI: Open doctor list
    UI->>View: Send search and filter parameters
    View->>DB: Query doctor profiles and schedules
    DB-->>View: Return matching doctors
    View-->>UI: Render doctor cards
    Patient->>UI: Select doctor and time slot
    UI->>View: Submit appointment form
    View->>DB: Create appointment request
    View->>Notify: Send confirmation notification
    Notify-->>Patient: Appointment confirmation
    Doctor->>UI: Open doctor dashboard
    UI->>View: Request appointment list
    View->>DB: Load appointments
    DB-->>View: Return appointment data
    View-->>UI: Show appointments
    Doctor->>UI: Approve or reject appointment
    UI->>View: Submit status update
    View->>DB: Update appointment status
    View->>Notify: Notify patient
```

## 10. Short Presentation Script

Use this short explanation while showing the diagrams:

```text
This is the overall use case diagram of my system. The system has three main actors: patient, doctor, and administrator. Patients can search doctors, book appointments, manage appointment history, and use AI tools. Doctors can manage schedules, review appointments, and update medical records. Administrators can manage users, doctor profiles, appointments, and system statistics.

The system workflow starts from the home page. After authentication, the system redirects users based on their role. Each role has a different dashboard and different permissions. This role-based design helps protect data and makes the workflow clear for each type of user.

For the appointment workflow, the patient searches and filters doctors, selects an available time slot, and submits an appointment request. The system stores the request in the database and sends a notification. Then the doctor can review and approve or reject the appointment from the doctor dashboard.

The AI module is designed as a support feature. It includes chatbot consultation and preliminary screening. It does not replace doctors, but it helps users receive initial guidance before meeting medical professionals.
```

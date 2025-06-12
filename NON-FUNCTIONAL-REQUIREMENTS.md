## 🚀 C.A.R.E – Clinical Appointment and Record Entry Non-Functional Requirements (NFR)

These define **how** the system performs or behaves:

### 1. **Performance**

-   [ ] NFR1.1: The system shall support **simultaneous use by at least 100 users** without performance degradation.
-   [ ] NFR1.2: Page load times shall not exceed **2 seconds** under normal operating conditions.

### 2. **Scalability**

-   [ ] NFR2.1: The system shall be designed to **scale** across multiple clinics or branches in the future.

### 3. **Security**

-   [ ] NFR3.1: The system shall **encrypt patient data** both at rest and in transit.
-   [ ] NFR3.2: The system shall enforce **two-factor authentication** for admin and doctor logins.
-   [ ] NFR3.3: The system shall implement **role-based access control** to ensure users only access permitted data.

### 4. **Availability**

-   [ ] NFR4.1: The system shall have **99.9% uptime** annually.
-   [ ] NFR4.2: The system shall include **automated backups** taken daily.

### 5. **Usability**

-   [ ] NFR5.1: The system shall provide a **user-friendly interface** suitable for non-technical medical staff.
-   [ ] NFR5.2: The system shall be accessible via **desktop, tablet, and mobile** devices.

### 6. **Maintainability**

-   [ ] NFR6.1: The system codebase shall follow **modular and documented structure** for easy updates and debugging.
-   [ ] NFR6.2: System updates should not require more than **15 minutes of downtime**.

### 7. **Compliance**

-   [ ] NFR7.1: The system shall comply with relevant health data regulations (e.g., **Republic Act No. 10173 - Data Privacy Act of 2012** in the Philippines).

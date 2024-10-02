# Library Management System v2 MAD 2 Project

## Description

This multi-user web application facilitates the management and access of e-books in an online library setting. It empowers librarians to organize sections, add and edit e-books, control user access, and monitor library activity. General users can search and browse e-books, request access, view issued books, and provide feedback.

## Key Features

* **Role-Based Access Control (RBAC):** Ensures secure access with separate functionalities for librarians and general users.
* **Librarian Dashboard:** Provides an overview of key library statistics, including active users, grant requests, e-books issued, and revoked.
* **Section Management:** Enables librarians to create, update, and delete sections for categorizing e-books.
* **E-book Management:** Allows librarians to create, edit, and delete e-books with detailed information like title, content, authors, and metadata.
* **Search Functionality:** Users can search for relevant e-books based on section, author, title, or other criteria.
* **User Request and Access Control:** Users can request specific e-books, with a maximum of 5 requests at a time. Librarians can grant/revoke access based on availability and library policies.
* **User Feedback:** Users can rate e-books to provide feedback and assist other users.
* **Automatic/Manual E-book Return System:** Choose either automatic revoking after a predefined period (e.g., 7 days) or manual revoking by librarians.
* **Daily Reminders:** Users receive daily notifications (via Google Chat Webhooks, SMS, or email) reminding them to access or return e-books approaching their due date.
* **Monthly Activity Reports:** Librarians receive monthly reports via email, summarizing key library activities like sections and e-books issued, return dates, and e-book ratings.

## Technologies

* **Frontend:** Vue.js
* **Backend:** Flask
* **Database:** SQLite
* **Styling:** Bootstrap
* **Background Tasks:** Celery 

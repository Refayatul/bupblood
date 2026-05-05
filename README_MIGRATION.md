# 🚀 Migration & Deployment Guide

This guide will help you migrate your BUP Blood Bank application from local SQLite to Supabase (PostgreSQL) and deploy it to Vercel.

## Phase 1: Supabase Setup

1.  **Create a Supabase Project**
    *   Go to [supabase.com](https://supabase.com) and create a new project.
    *   Note down your **Project URL** and **API Key** (anon/public).
    *   Go to **Project Settings > Database** and copy the **Connection String (URI)**. It looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

2.  **Create Storage Bucket**
    *   Go to **Storage** in the Supabase dashboard.
    *   Create a new bucket named `images`.
    *   **IMPORTANT:** Make the bucket **Public**.
    *   (Optional) Set a policy to allow public read access if not automatic.

3.  **Get Service Role Key (For Migration)**
    *   Go to **Project Settings > API**.
    *   Copy the `service_role` secret. This is needed for the migration script to bypass Row Level Security (RLS) and upload files without logging in.

## Phase 2: Local Configuration

1.  **Update `.env` File**
    Create or update your `.env` file in the project root with the following:

    ```env
    # Supabase Configuration
    SUPABASE_URL=https://your-project-ref.supabase.co
    SUPABASE_KEY=your-service-role-key-here
    
    # Database Connection (PostgreSQL)
    SQLALCHEMY_DATABASE_URI=postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres
    
    # Flask Security
    SECRET_KEY=your-secret-key-here
    ```

2.  **Install Dependencies**
    Ensure you have the required packages:
    ```bash
    pip install psycopg2-binary supabase python-dotenv
    ```

## Phase 3: Database Migration

1.  **Create Tables in Supabase**
    Run the Flask migration command to create the schema in your new PostgreSQL database:
    ```bash
    flask db upgrade
    ```
    *Note: If `flask db upgrade` fails, you might need to run `flask db init` and `flask db migrate` first, or manually create the tables. But `upgrade` should work if migrations folder exists.*

2.  **Run the Data Migration Script**
    Execute the script I created for you:
    ```bash
    python migrate_to_supabase.py
    ```
    *   This script will:
        *   Read all users from `instance/bup_blood_bank.db`.
        *   Upload local images to the `images` bucket in Supabase.
        *   Insert user records into the PostgreSQL database with updated image URLs.
        *   Migrate donation history.

## Phase 4: Vercel Deployment

1.  **Prepare for Vercel**
    *   Ensure `requirements.txt` is up to date: `pip freeze > requirements.txt`
    *   Ensure `vercel.json` is present (I've checked it, it looks good).

2.  **Push to GitHub**
    *   Commit and push your latest changes to GitHub.

3.  **Deploy on Vercel**
    *   Go to [vercel.com](https://vercel.com) and "Add New Project".
    *   Import your GitHub repository.
    *   **Environment Variables:** Add the following in the Vercel project settings:
        *   `SQLALCHEMY_DATABASE_URI`: (Your Supabase connection string)
        *   `SECRET_KEY`: (Your secret key)
        *   `SUPABASE_URL`: (Your Supabase URL)
        *   `SUPABASE_KEY`: (Your Supabase Anon Key - for the app to use, not service role)
    *   **Deploy!**

## Troubleshooting

*   **Image Uploads:** If images fail to upload, check if the `images` bucket exists and is public.
*   **Database Connection:** Double-check your password in the connection string. Special characters might need URL encoding.

# BloodBank Project Memory Bank

## Project Overview
**Name:** BUP Blood Bank  
**Type:** Flask Web Application  
**Purpose:** Blood donor management system for Bangladesh University of Professionals (BUP)  
**Admin Email:** refayat.connect@gmail.com  

## AI Agent Preferences

### Shell
- **Always use Git Bash** for running commands in this project
- Invoke via: `& "C:\Program Files\Git\bin\bash.exe" -c "your command here"`
- Git Bash supports Unix tools: `grep`, `awk`, `sed`, `find`, `cat`, `ls`, etc.
- **Do NOT use PowerShell 5.1** (default) — it causes false errors on git stderr output
- PowerShell 7 (`pwsh`) is available but Git Bash is preferred for this project

**Last shell preference set:** 13 Apr 2026, 13:38 BDT



## Current Status

### Technology Stack
- **Backend:** Flask (Python)
- **Database:** SQLite (local) → Supabase PostgreSQL (production)
- **Image Storage:** Local static files → Supabase Storage (production)
- **Hosting:** Vercel (planned)
- **Domain:** OVH (to be purchased)

### Database Schema
**User Model:**
- `id` (Primary Key)
- `student_id` (Unique, used as username)
- `name`
- `department`
- `batch`
- `blood_group`
# BloodBank Project Memory Bank

## Project Overview
**Name:** BUP Blood Bank  
**Type:** Flask Web Application  
**Purpose:** Blood donor management system for Bangladesh University of Professionals (BUP)  
**Admin Email:** refayat.connect@gmail.com  

## AI Agent Preferences

### Shell
- **Always use Git Bash** for running commands in this project
- Invoke via: `& "C:\Program Files\Git\bin\bash.exe" -c "your command here"`
- Git Bash supports Unix tools: `grep`, `awk`, `sed`, `find`, `cat`, `ls`, etc.
- **Do NOT use PowerShell 5.1** (default) — it causes false errors on git stderr output
- PowerShell 7 (`pwsh`) is available but Git Bash is preferred for this project

**Last shell preference set:** 13 Apr 2026, 13:38 BDT



### Version: 3.3 (13 Apr 2026)

### Technology Stack
- **Backend:** Flask (Python)
- **Database:** Supabase PostgreSQL (Production)
- **Official Program List:** Standardized BUP Hierarchy (v3.3)

### Features Implemented

#### Data Management
✅ **Official Program List (v3.3):** Updated `PROGRAM_DATA` with the full official university list (Undergraduate & Graduate).
✅ **Conservative Data Migration:** Successfully migrated 50 official titles while preserving hundreds of legacy "Unknown" department names as requested.
✅ **Local User Backup:** Automated local backup of Supabase user table before structural changes.

#### User Features
✅ Registration with password  
✅ Login system  
✅ User dashboard  
✅ Profile updates  
✅ **Dynamic Availability** (120-day / 4-month cooldown enforced mathematically)  
✅ **Profile Visibility Toggle** (Self-service hide/show)  


✅ **Self-Service Password Reset** (ID + Mobile + Dept + Blood Group verification)  
✅ **Password Strength Indicator**  
✅ **Mobile Menu with Auth State**  

#### Admin Features
✅ Admin panel (`/admin`)  
✅ Approve/Reject new registrations  
✅ Hardcoded admin login: `admin` / `adminpassword`  

#### Public Features
✅ View approved donors  
✅ Search by blood group  
✅ Donor cards with availability status  
✅ Call donors directly (tel: links)  

## User Authentication Flow

### New Users (Registered after updates)
1. User registers with Student ID, password, email, and other info
2. Admin approves via admin panel
3. User can log in with Student ID + password
4. Access dashboard to update availability & profile picture

### Existing Users (441 users from old database)
1. **Status:** All have random secure passwords set via script
2. **Passwords stored in:** `temp_passwords.txt` (DELETE after use!)
3. **Login process:**
   - User can't log in initially (no password knowledge)
   - User emails **refayat.connect@gmail.com** with ID card
   - Admin verifies identity & sends temporary password
   - User logs in -> Changes password in Dashboard
   - **NOTE:** Existing users DO NOT have emails in DB, so self-service reset won't work for them until they update their profile.

## Password Reset Workflow

**For users who forgot password:**
1. User clicks "Forgot Password?" on login page
2. Enters: Student ID, Mobile, Dept, Blood Group
3. System verifies details against DB
4. **If User has Email:**
   - System shows masked email (e.g. `a***b@gmail.com`)
   - User confirms full email
   - System allows password reset
5. **If User has NO Email (Old users):**
   - System verifies other details
   - System allows password reset (Identity verified via other fields)

## File Structure

```
BloodBank/
├── app.py                          # Main application
├── models.py                       # Database models (Added email field)
├── forms.py                        # WTForms (Added ForgotPassword, VerifyEmail, ResetPassword)
├── config.py                       # Color palette config
├── requirements.txt                # Python dependencies
├── vercel.json                     # Vercel deployment config
├── .env.example                    # Environment variables template
├── set_default_passwords.py        # Script to set passwords for old users
├── temp_passwords.txt              # ⚠️ SECURE - Delete after use!
├── instance/
│   └── bup_blood_bank.db          # SQLite database (local only)
├── migrations/                     # Database migration files
├── static/
│   └── images/                    # User profile images (local only)
├── templates/
│   ├── base.html                  # Base template with navigation
│   ├── home.html                  # Homepage with donor list
│   ├── register.html              # Registration form
│   ├── user_login.html            # User login form
│   ├── dashboard.html             # User dashboard (Added image upload)
│   ├── donor_card.html            # Donor card component
│   ├── admin_panel.html           # Admin approval panel
│   ├── login.html                 # Admin login
│   ├── about.html                 # About page
│   ├── contact.html               # Contact page
│   ├── tos.html                   # Terms of Service
│   ├── change_password.html       # Change password form
│   ├── forgot_password.html       # Identity verification form
│   ├── verify_email.html          # Email confirmation form
│   └── reset_password.html        # New password form
└── utils/
    └── color_palettes.json        # UI color configuration
```

## Environment Variables (for production)

```env
SECRET_KEY=your-secret-key
SQLALCHEMY_DATABASE_URI=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_KEY=[YOUR-ANON-KEY]
```

## Deployment Plan (Vercel + Supabase)

### Step 1: Supabase Setup
1. Create project at supabase.com
2. **Database:** Copy connection string from Settings > Database
3. **Storage:**
   - Create bucket named `images`
   - Set to **Public**
4. **API Keys:** Copy Project URL and `anon` key from Settings > API

### Step 2: Data Migration (SQLite → Supabase)
- **TODO:** Create migration script to:
  1. Read all users from `instance/bup_blood_bank.db`
  2. Upload to Supabase PostgreSQL
  3. Upload images from `static/images/` to Supabase Storage
  4. Update image URLs in database

### Step 3: Vercel Deployment
1. Push code to GitHub
2. Import repo to Vercel
3. Add environment variables
4. Deploy
5. Connect custom OVH domain

## Important Files to Secure

⚠️ **NEVER commit to GitHub:**
- `temp_passwords.txt` (contains all user passwords)
- `.env` (contains API keys)
- `instance/bup_blood_bank.db` (contains user data)

✅ **Add to .gitignore:**
```
temp_passwords.txt
.env
instance/
venv/
__pycache__/
*.pyc
```

## Known Issues / TODO

### High Priority
1. ❌ **Add "Change Password" feature to user dashboard**
2. ❌ **Create data migration script (SQLite → Supabase)**
3. ❌ **Update mobile navigation menu with login/logout links**
4. ❌ **Add .gitignore file**

### Medium Priority
5. ❌ **Add email verification for new registrations**
6. ❌ **Add password strength requirements**
7. ❌ **Add "Remember Me" option on login**
8. ❌ **Improve error messages**

### Low Priority
9. ❌ **Add profile picture upload in dashboard**
10. ❌ **Add donation history tracking**
11. ❌ **Add blood request system**

## Local Development

### Setup
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies (minimal for local)
pip install Flask Flask-Login Flask-SQLAlchemy Flask-WTF Flask-Migrate WTForms Pillow python-dotenv pytz

# Run database migrations
flask db migrate -m "description"
flask db upgrade

# Run app
python app.py
```

### Access Points
- **Homepage:** http://localhost:5000
- **User Login:** http://localhost:5000/user/login
- **User Register:** http://localhost:5000/register
- **Admin Login:** http://localhost:5000/login
- **Admin Panel:** http://localhost:5000/admin

### Admin Credentials
- Username: `admin`
- Password: `adminpassword`
- **TODO:** Change these before production!

## Statistics
- **Total Users:** 441 (as of last script run)
- **All users have passwords:** ✅ Yes
- **Users approved:** Check via admin panel or database

## Recent Changes (Git History)

### Branch: `Dev` (active) — Latest commits on origin/Dev

| Commit | Date | Description |
|--------|------|-------------|
| `0da6fd3` | 13 Apr 2026 | Update admin_filter template |
| `427c6bc` | 13 Apr 2026 | fix: Swal dialog now shows correct Hide/Unhide text based on current profile state |
| `99cce20` | 13 Apr 2026 | feat: **Triple-Soft Architecture** — full soft-delete implementation |
| `001cebe` | 13 Apr 2026 | feat: Enhance UI with SweetAlert2 and add quick availability toggle |
| `02fa144` | 12 Apr 2026 | fix: Issue with updating user blood group |
| `f613800` | 12 Apr 2026 | Updated SQLAlchemy to 2.0.45 (also on `main`) |
| `28082f4` | 09 Dec 2025 | Changed "available" to "want" label |
| `2d1558c` | 09 Dec 2025 | Trying to implement multisearch and admin log |
| `13b3991` | 09 Dec 2025 | feat: Add admin panel with user search, filtering, activity log, last login/availability tracking |
| `beb9820` | 09 Dec 2025 | feat: Add initial home page with guest/authenticated views, statistics, CTAs |

*Last update by AI (BUP_Blood_Bank_Assistant): 13 Apr 2026, 16:42 BDT*
*Version: 3.2*

### v3.2 - Dynamic Availability & User Privacy
- **Dynamic 120-Day Cooldown:** Replaced manual availability toggling with mathematical calculation based on `last_donation_date`.
- **4-Month Messaging:** Standardized all UI messages to "4 months" for better readability.
- **User Visibility Toggle:** Exposed the `is_archived` status to users, allowing them to hide their own profiles from search results.
- **SweetAlert2 Context:** Confirmation dialogs now correctly reflect "Hide/Unhide" actions.

### Key Features Added Recently (Apr 2026):
1. ✅ **Triple-Soft Architecture** — soft-delete for users (hide/delete without data loss)
2. ✅ **SweetAlert2 (Swal)** dialogs — used for confirmations (hide/unhide/delete)
3. ✅ **Hide/Unhide profile toggle** in admin panel with correct dynamic button label
4. ✅ **Quick availability toggle** from admin panel
5. ✅ **Admin filter page** (`admin_filter.html`) — improved UI for filtering users
6. ✅ **SQLAlchemy upgraded** to 2.0.45

### What Needs to Be Done Next:
1. Merge `Dev` → `main` after testing
2. Test full Triple-Soft Architecture flow (hide → restore → delete)
3. Deploy to Vercel with Supabase
4. Connect custom domain

## Contact & Support
- **Admin Email:** refayat.connect@gmail.com
- **Original Developer Email (old):** ucchash.connect@gmail.com
- **Project Type:** Blood donation management
- **License:** TBD (recommended MIT for humanitarian projects)

---
**Last Updated:** 13 Apr 2026, 16:04 BDT  
**Version:** 3.1 (Dynamic 120-Day / 4-Month Availability + SweetAlert2 Prompts)


---

## Dynamic Availability Architecture (v3.1)

### The Problem
Previously, a donor would become "Unavailable" after donating, but would stay that way forever unless they remembered to toggle it back manually. Background jobs (cron) were considered but rejected as too complex to maintain on serverless hosting.

### The Solution: Mathematical Availability
Instead of "flipping a bit" at a specific time, the system now calculates availability on-the-fly both in display and in queries.

#### 1. Database Model (`models.py`)
- Added `@property is_actually_available`:
  - Returns `True` IF (`is_available` is True) AND (`last_donation_date` is > 120 days / 4 months ago or NULL).
  - This ensures universal consistency for front-end badges.

#### 2. Backend Queries (`app.py`)
- **Homepage & Search:** Both now globally filter results to only show donors where:
  - `is_available == True`
  - AND (`last_donation_date` is NULL OR `last_donation_date <= date.today() - 120 days / 4 months`)
- This means a donor effectively "disappears" from the public lists for 120 days / 4 months after logging a donation, then "magically" reappears on the 121st day.

#### 3. UX Flow (`profile.html` & `app.py`)
- **Submission Interception:** In `profile.html`, the "Add Donation" form is intercepted by **SweetAlert2**.
- **User Prompt:** The user is asked: *"Would you like your profile to automatically appear as 'Available' again after 4 months?"*

- **Auto-Update:** 
  - If **YES**: `is_available` remains `True`. (The 120-day cooldown hides them automatically).
  - If **NO**: `is_available` is set to `False`. (They remain hidden even after 120 days / 4 months until manual toggle).


### Reversibility
To revert this feature:
1. Remove the filtering logic from `home()` and `search()` routes in `app.py`.
2. Change `donor_card.html` to use `user.is_available` instead of `user.is_actually_available`.
3. Remove the JavaScript interception in `profile.html`.

## Data Standardization Logic (v3.4.0)

### BUP Student ID Structure
Identified the following patterns to distinguish program levels and departments:

#### **Program Level Digits (3rd Digit)**
- **Digit `1`**: **Undergraduate** (FASS, FSSS faculties)
- **Digit `4`**: **Undergraduate** (FSSS faculty specific: Law, IR, MCJ)
- **Digit `5`**: **Undergraduate** (FST / CSE batch 2022+) or **Graduate** (others like ICT/MICT)
- **Digit `2`**: **Undergraduate** (FBS faculty: BBA Majors)

#### **Verified Department Codes (Final Truth Table)**
| DEPT CODE | DEPARTMENT | LEVEL DIGIT | FACULTY |
| :--- | :--- | :--- | :--- |
| **118** | Sociology | 1 | FASS |
| **488** / **1488** | Economics | 1 | FASS |
| **1424** | Economics | 1 | FASS (Masters) |
| **1694** / **694** / **631** | Public Admin | 1 / 4 | FASS / FSSS |
| **593** / **1117** / **110** | English / IR (Old) | 1 / 4 | FASS / FSSS |
| **192** / **110** / **125** | Int. Relations | 4 | FSSS |
| **295** / **4295** | Law (LLB) | 4 | FSSS |
| **319** / **4319** | Mass Comm (MCJ) | 4 | FSSS |
| **389** / **1347** / **1310** | DMR / DHSM | 1 / D | FASS |
| **296** / **209** | Dev Studies | 1 | FASS |
| **5242** / **5252** | CSE | 5 | FST |
| **5320** / **338** | Env Science | 5 | FST |
| **5490** / **5110** | ICE | 5 | FST |
| **2114** | BBA (AIS) | 2 | FBS |
| **2215** | BBA (Finance) | 2 | FBS |
| **2416** | BBA (Management) | 2 | FBS |
| **2517** | BBA (Marketing) | 2 | FBS |
| **2301** / **301** | BBA (General) | 2 | FBS |

### Migration Statistics
- **Total Users:** 496
- **Standardized:** **451 (91%)**
- **Unknowns Remaining:** 45 (Unfixable: Medical, National Uni, Missing IDs)

---
**Last Updated:** 13 Apr 2026, 22:38 BDT  
**Version:** 3.4.0 (Full Migration Complete)

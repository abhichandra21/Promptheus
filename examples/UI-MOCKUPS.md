# Promptheus Multi-User Platform - UI Mockups

## Screen Designs with ASCII Art + Detailed Descriptions

---

### 1. Login Page

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│                      ╔═══════════════╗                         │
│                      ║  PROMPTHEUS   ║                         │
│                      ╚═══════════════╝                         │
│               AI-Powered Prompt Engineering                    │
│                                                                │
│    ┌────────────────────────────────────────────────┐         │
│    │                                                │         │
│    │  Email                                         │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ you@example.com                         │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  Password                                      │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ ••••••••••••                             │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │          Sign In                         │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  ╔════════════════════════════════════════╗   │         │
│    │  ║ Demo Credentials:                      ║   │         │
│    │  ║ Email: demo@promptheus.dev             ║   │         │
│    │  ║ Password: DemoPassword123!             ║   │         │
│    │  ╚════════════════════════════════════════╝   │         │
│    │                                                │         │
│    │     Don't have an account? [Sign up]          │         │
│    └────────────────────────────────────────────────┘         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- **Gradient Background**: Indigo to purple gradient creating a modern, tech feel
- **Centered Card**: White rounded card with shadow for depth
- **Logo**: Prominent Promptheus branding with gradient text
- **Form Fields**: Clean, large input fields with focus states
- **Demo Box**: Light blue background box highlighting demo credentials
- **CTA Button**: Gradient button (indigo to purple) with hover effects
- **Responsive**: Mobile-first design, stacks on small screens

**Key Features:**
- Auto-focus on email field
- Password visibility toggle
- "Remember me" checkbox (optional)
- "Forgot password?" link
- Social login buttons (Google, GitHub) - Phase 2

---

### 2. Registration Page

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│                    Create Your Account                         │
│                    Join Promptheus Today                       │
│                                                                │
│    ┌────────────────────────────────────────────────┐         │
│    │                                                │         │
│    │  Email *                                       │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ you@example.com                         │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  Username *                                    │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ johndoe                                  │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  Full Name (optional)                          │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ John Doe                                 │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  Password * (min 12 characters)                │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ ••••••••••••••••                         │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │  ✓ Uppercase  ✓ Lowercase  ✓ Number  ✓ Symbol│         │
│    │                                                │         │
│    │  Confirm Password *                            │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │ ••••••••••••••••                         │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │  ┌──────────────────────────────────────────┐ │         │
│    │  │        Create Account                    │ │         │
│    │  └──────────────────────────────────────────┘ │         │
│    │                                                │         │
│    │     Already have an account? [Sign in]        │         │
│    └────────────────────────────────────────────────┘         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- Similar styling to login for consistency
- Password strength indicator with real-time validation
- Field validation on blur with error messages
- Success checkmarks for valid fields
- Disabled submit button until all required fields valid

---

### 3. Main Prompt Refinement Interface

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ╔═══════════════╗                    Welcome, johndoe!  |  History  |  👤  │
│ ║  PROMPTHEUS   ║                                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│         What would you like to create?                                     │
│         Enter your initial prompt and we'll help refine it                 │
│                                                                            │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │                                                                │     │
│    │  E.g., Write a blog post about AI in healthcare...            │     │
│    │                                                                │     │
│    │                                                                │     │
│    │                                                                │     │
│    │                                                                │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                                                                            │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │                 Refine My Prompt →                             │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                                                                            │
│                                                                            │
│    ┌─────────────────────────────────────────────────────────┐            │
│    │ 💡 Pro Tips:                                            │            │
│    │  • Be specific about your goal                          │            │
│    │  • Mention any constraints or requirements              │            │
│    │  • Our AI will ask clarifying questions                 │            │
│    └─────────────────────────────────────────────────────────┘            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Recent Prompts:                                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📝 Blog post about machine learning trends   | 2 days ago │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📝 Email campaign for product launch         | 5 days ago │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📝 Code review guidelines                     | 1 week ago │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- **Clean Header**: Logo, user greeting, navigation links
- **Hero Section**: Large text area for prompt input
- **Prominent CTA**: Gradient button that stands out
- **Pro Tips**: Helpful guidance for new users
- **Recent Prompts**: Quick access to history (collapsible)
- **Floating Action Button**: Quick "New Prompt" button always visible

---

### 4. Questions Step

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ╔═══════════════╗                    Welcome, johndoe!  |  History  |  👤  │
│ ║  PROMPTHEUS   ║                                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│         Help us understand your needs                                      │
│         Answer a few questions to get the best refined prompt              │
│                                                                            │
│    ┌────────────────────────────────────────────────────────────────┐     │
│    │                                                                │     │
│    │  1. What is the target audience for this content?             │     │
│    │                                                                │     │
│    │  ┌──────────────────────────────────────────────────────────┐ │     │
│    │  │ Healthcare professionals and patients                   │ │     │
│    │  └──────────────────────────────────────────────────────────┘ │     │
│    │                                                                │     │
│    │  2. What tone should be used?                                  │     │
│    │                                                                │     │
│    │  ○ Professional    ● Technical    ○ Casual    ○ Creative      │     │
│    │                                                                │     │
│    │  3. Desired length? (optional)                                 │     │
│    │                                                                │     │
│    │  ○ Short (1-2 paragraphs)                                      │     │
│    │  ● Medium (3-5 paragraphs)                                     │     │
│    │  ○ Long (6+ paragraphs)                                        │     │
│    │                                                                │     │
│    │  4. Key topics to cover? (optional)                            │     │
│    │                                                                │     │
│    │  ☑ Diagnosis    ☑ Treatment    ☐ Prevention    ☐ Research     │     │
│    │                                                                │     │
│    └────────────────────────────────────────────────────────────────┘     │
│                                                                            │
│    ┌──────────────────┐  ┌────────────────────────────────────────┐       │
│    │  ← Back          │  │  Generate Refined Prompt →             │       │
│    └──────────────────┘  └────────────────────────────────────────┘       │
│                                                                            │
│    Progress: ████████████████░░░░ 80% complete                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- **Question Cards**: Each question in a clean card layout
- **Multiple Input Types**: Text, radio, checkbox based on question type
- **Visual Indicators**: Required vs optional clearly marked
- **Progress Bar**: Shows completion percentage
- **Dual CTA**: Back button and primary action button
- **Auto-save**: Draft answers saved in case of navigation away

---

### 5. Refined Result Page

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ╔═══════════════╗                    Welcome, johndoe!  |  History  |  👤  │
│ ║  PROMPTHEUS   ║                                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Your Original Prompt                                                │  │
│  │                                                                     │  │
│  │ Write a blog post about AI in healthcare                           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌═════════════════════════════════════════════════════════════════════┐  │
│  ║ Refined Prompt                                       📋 Copy        ║  │
│  ║                                                                     ║  │
│  ║ Write a comprehensive, technically-focused blog post (3-5          ║  │
│  ║ paragraphs) about artificial intelligence applications in          ║  │
│  ║ healthcare, targeting both healthcare professionals and patients.  ║  │
│  ║                                                                     ║  │
│  ║ Focus Areas:                                                        ║  │
│  ║ - AI-powered diagnostic tools and their accuracy improvements      ║  │
│  ║ - Treatment personalization through machine learning               ║  │
│  ║ - Real-world case studies and success stories                      ║  │
│  ║                                                                     ║  │
│  ║ Tone and Style:                                                     ║  │
│  ║ - Use technical terminology with clear explanations                ║  │
│  ║ - Balance scientific rigor with accessibility                      ║  │
│  ║ - Include statistics and research citations where relevant         ║  │
│  ║                                                                     ║  │
│  ║ Structure:                                                          ║  │
│  ║ 1. Introduction: Current state of AI in healthcare                 ║  │
│  ║ 2. Diagnosis: How AI improves accuracy and speed                   ║  │
│  ║ 3. Treatment: Personalization and optimization                     ║  │
│  ║ 4. Challenges and ethical considerations                           ║  │
│  ║ 5. Future outlook and emerging trends                              ║  │
│  ╚═════════════════════════════════════════════════════════════════════╝  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ 🎨 Want to tweak it?                                                │  │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │ │ E.g., "Make it more casual" or "Add a section about privacy"   │ │  │
│  │ └─────────────────────────────────────────────────────────────────┘ │  │
│  │ [Apply Tweak]                                                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────┐  ┌────────────────────────┐                     │
│  │  ← Create New Prompt │  │  View History →        │                     │
│  └──────────────────────┘  └────────────────────────┘                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- **Before/After**: Original prompt in gray box, refined in highlighted gradient box
- **Copy Button**: One-click clipboard copy with visual feedback
- **Iterative Refinement**: Tweak input box for quick adjustments
- **Visual Hierarchy**: Refined prompt is the star, stands out with color/border
- **Action Buttons**: Clear next steps (new prompt or view history)

---

### 6. History Page

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ╔═══════════════╗                    Welcome, johndoe!  |  History  |  👤  │
│ ║  PROMPTHEUS   ║                                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  ← Back            Prompt History                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┬─────────────────────────────────────────────────────┐
│                      │                                                     │
│  ┌────────────────┐  │  ┌───────────────────────────────────────────────┐ │
│  │ Jan 15, 2025   │  │  │ Prompt Details                                │ │
│  │                │  │  │ Created Jan 15, 2025 at 2:30 PM              │ │
│  │ Blog post about│  │  │                                    🗑️ Delete   │ │
│  │ AI in health...│  │  └───────────────────────────────────────────────┘ │
│  │                │  │                                                     │
│  │ [gemini] [gen] │  │  Original Prompt                                   │
│  └────────────────┘  │  ┌───────────────────────────────────────────────┐ │
│                      │  │ Write a blog post about AI in healthcare     │ │
│  ┌────────────────┐  │  └───────────────────────────────────────────────┘ │
│  │ Jan 14, 2025   │  │                                                     │
│  │                │  │  Refined Prompt                                    │
│  │ Email campaign │  │  ┌═══════════════════════════════════════════════┐ │
│  │ for product...  │  │  ║ Write a comprehensive, technically-focused   ║ │
│  │                │  │  ║ blog post (3-5 paragraphs) about artificial  ║ │
│  │ [claude] [gen] │  │  ║ intelligence applications in healthcare...   ║ │
│  └────────────────┘  │  ║                                               ║ │
│                      │  ║ [Full refined prompt content here...]        ║ │
│  ┌────────────────┐  │  ╚═══════════════════════════════════════════════╝ │
│  │ Jan 10, 2025   │  │                                                     │
│  │                │  │  ┌───────────────────────────────────────────────┐ │
│  │ Code review    │  │  │  📋 Copy Refined Prompt                       │ │
│  │ guidelines     │  │  └───────────────────────────────────────────────┘ │
│  │                │  │                                                     │
│  │ [openai] [ana] │  │  Metadata:                                         │
│  └────────────────┘  │  Provider: Gemini                                  │
│                      │  Model: gemini-2.0-flash-exp                       │
│  ┌────────────────┐  │  Task Type: Generation                             │
│  │ Jan 8, 2025    │  │  Shared: No                                        │
│  │                │  │                                                     │
│  │ ...            │  │                                                     │
│  └────────────────┘  │                                                     │
│                      │                                                     │
│  [Load More...]      │                                                     │
│                      │                                                     │
└──────────────────────┴─────────────────────────────────────────────────────┘
```

**Design Details:**
- **Two-Column Layout**: List on left, detail on right
- **List Items**: Date, truncated prompt, tags for provider/task type
- **Active Selection**: Highlighted item shows in detail pane
- **Detail View**: Full original and refined prompts with metadata
- **Quick Actions**: Copy button, delete button
- **Infinite Scroll**: Load more as user scrolls
- **Search/Filter**: (Phase 2) Filter by date, provider, task type

---

### 7. User Profile / Settings

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ╔═══════════════╗                    Welcome, johndoe!  |  History  |  👤  │
│ ║  PROMPTHEUS   ║                                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  ← Back            Account Settings                                        │
└────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Profile Information                                                 │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Email: johndoe@example.com                          [Verified] │  │
│  │ Username: johndoe                                              │  │
│  │ Full Name: John Doe                                            │  │
│  │ Member Since: Jan 1, 2025                                      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Team / Organization                                                 │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Team: Acme Inc                                      [Admin]    │  │
│  │ Members: 5 / 10                                                │  │
│  │ Plan: Team ($49/month)                                         │  │
│  │                                                                │  │
│  │ [Manage Team] [Invite Members] [Upgrade Plan]                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  API Keys (for CLI)                                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ┌──────────────────────────────────────────────────────────┐   │  │
│  │ │ Production Key     sk-live-ABCDxxx...  Last used: Today  │   │  │
│  │ │ Created: Jan 1      [Revoke]                             │   │  │
│  │ └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │ ┌──────────────────────────────────────────────────────────┐   │  │
│  │ │ Development Key    sk-test-XYZWxxx...  Last used: 2d ago │   │  │
│  │ │ Created: Dec 28     [Revoke]                             │   │  │
│  │ └──────────────────────────────────────────────────────────┘   │  │
│  │                                                                │  │
│  │ [+ Create New API Key]                                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Usage This Month                                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Prompts Refined: 1,247 / 10,000                                │  │
│  │ ██████████████░░░░░░░░ 12%                                     │  │
│  │                                                                │  │
│  │ API Calls: 3,892 / 50,000                                      │  │
│  │ ████░░░░░░░░░░░░░░░░░░ 8%                                      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Preferences                                                         │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Default Provider:  [Gemini ▼]                                  │  │
│  │ Default Model:     [gemini-2.0-flash-exp ▼]                    │  │
│  │ Email Notifications: ☑ Enabled                                 │  │
│  │ History Auto-Save:   ☑ Enabled                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  [Save Changes]  [Change Password]  [Delete Account]                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Design Details:**
- **Sections**: Profile, Team, API Keys, Usage, Preferences
- **API Key Management**: Show prefix only, revoke button, creation date
- **Usage Metrics**: Visual progress bars showing consumption
- **Team Management**: Members, plan info, upgrade CTA
- **Preferences**: Dropdown selects for defaults, toggles for settings

---

### 8. CLI Authentication Flow (Terminal UI)

```bash
$ promptheus login

╔═══════════════════════════════════════════════════════════════╗
║                        PROMPTHEUS                             ║
║                   CLI Authentication                          ║
╚═══════════════════════════════════════════════════════════════╝

Choose authentication method:
  1. Browser-based login (recommended)
  2. API key
  3. Email/Password

Your choice [1]: 1

Opening browser for authentication...
Please complete login in your browser.

Waiting for approval... [████████████████░░░░] 80%

✓ Authentication successful!

╔═══════════════════════════════════════════════════════════════╗
║  Logged in as: john@example.com                               ║
║  Team: Acme Inc                                               ║
║  Plan: Team                                                   ║
║  API Usage: 1,247 / 10,000 prompts this month                 ║
╚═══════════════════════════════════════════════════════════════╝

Credentials saved to ~/.promptheus/auth.json

$ promptheus "Generate a prompt"
# Works authenticated!
```

---

## Color Palette

```
Primary:
- Indigo 600: #4F46E5
- Purple 600: #9333EA

Gradients:
- Primary: Linear gradient from Indigo 600 to Purple 600
- Background: Indigo 100 → Purple 50 → Pink 100

Grays:
- Gray 50:  #F9FAFB (backgrounds)
- Gray 100: #F3F4F6 (secondary backgrounds)
- Gray 300: #D1D5DB (borders)
- Gray 600: #4B5563 (secondary text)
- Gray 900: #111827 (primary text)

Status:
- Success Green: #10B981
- Error Red:     #EF4444
- Warning Yellow: #F59E0B
- Info Blue:     #3B82F6
```

---

## Typography

```
Headings:
- H1: 2.25rem (36px) - Bold
- H2: 1.875rem (30px) - Bold
- H3: 1.5rem (24px) - Semibold
- H4: 1.25rem (20px) - Semibold

Body:
- Large: 1.125rem (18px) - Regular
- Base: 1rem (16px) - Regular
- Small: 0.875rem (14px) - Regular
- Tiny: 0.75rem (12px) - Medium

Font Stack:
- Primary: Inter, system-ui, sans-serif
- Code: 'Fira Code', 'Consolas', monospace
```

---

## Interactive States

### Buttons
```
Default:     bg-indigo-600  text-white
Hover:       bg-indigo-700  shadow-md  transform: scale(1.02)
Active:      bg-indigo-800  shadow-sm  transform: scale(0.98)
Disabled:    bg-gray-300    text-gray-500  cursor-not-allowed
Loading:     bg-indigo-600  text-white  [spinner animation]
```

### Input Fields
```
Default:     border-gray-300  focus:ring-2  focus:ring-indigo-500
Error:       border-red-500   focus:ring-red-500
Success:     border-green-500 focus:ring-green-500
Disabled:    bg-gray-100      cursor-not-allowed
```

### Cards
```
Default:     bg-white  shadow  rounded-xl
Hover:       shadow-md  transform: translateY(-2px)
Active:      ring-2  ring-indigo-500
```

---

## Responsive Breakpoints

```
Mobile:      < 640px   - Stack vertically, full-width buttons
Tablet:      640-1024  - Two-column grids, larger touch targets
Desktop:     > 1024    - Three-column grids, hover effects
```

---

## Animations

### Page Transitions
- Fade in: 200ms ease-in
- Slide up: 300ms ease-out
- Scale: 150ms ease-in-out

### Loading States
- Spinner: Continuous rotation
- Skeleton screens: Pulse animation (1.5s)
- Progress bars: Smooth transition

### Micro-interactions
- Button click: Scale down → up (100ms)
- Copy to clipboard: Checkmark fade in → out (2s)
- Notification toast: Slide in from right → fade out (3s)

---

## Accessibility

- **ARIA Labels**: All interactive elements
- **Keyboard Navigation**: Tab order, focus visible
- **Screen Reader**: Semantic HTML, alt text
- **Color Contrast**: WCAG AA compliant (4.5:1)
- **Error Messages**: Clear, actionable
- **Loading States**: Announced to screen readers

---

## Mobile Considerations

- **Touch Targets**: Minimum 44x44px
- **Viewport**: Responsive meta tag
- **Fonts**: System fonts for performance
- **Gestures**: Swipe for navigation (history)
- **Offline**: Service worker for basic offline support (Phase 2)

---

These mockups represent the complete user journey from authentication through prompt refinement to history management. The design emphasizes clarity, ease of use, and a modern aesthetic that appeals to both technical and non-technical users.

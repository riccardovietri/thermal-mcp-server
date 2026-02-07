# 🚀 QUICK START: Using Claude Code & Cowork for Thermal MCP Server

## DAY 1 - GET STARTED RIGHT NOW (30 minutes)

### Step 1: Create Project (5 min)

```bash
# Create and enter project directory
cd ~/projects  # or wherever you keep projects
mkdir thermal-mcp-server
cd thermal-mcp-server

# Initialize git
git init
echo "venv/" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".pytest_cache/" >> .gitignore
echo ".env" >> .gitignore

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# OR: venv\Scripts\activate  # Windows

# Create structure
mkdir -p src/models tests docs examples
touch src/__init__.py src/models/__init__.py
```

### Step 2: Copy Files I Created (5 min)

I've created 2 essential files for you:

1. **thermal-mcp-project-plan.md** - Your complete 7-day sprint plan
2. **coldplate_model.py** - Your starter thermal model code

Copy these from the outputs directory to your project:

```bash
# Get the files I created
# (They're in your outputs directory from this conversation)

# Copy project plan to your project root
cp /path/to/thermal-mcp-project-plan.md ./PROJECT_PLAN.md

# Copy thermal model to src
cp /path/to/coldplate_model.py ./src/models/coldplate.py
```

### Step 3: Install Dependencies (5 min)

```bash
# Install FastMCP and dependencies
pip install fastmcp numpy pytest

# Verify installation
python -c "import fastmcp; print('FastMCP installed!')"
```

### Step 4: Test Thermal Model (5 min)

```bash
# Run the example thermal calculation
cd src/models
python coldplate.py

# You should see thermal analysis output!
```

### Step 5: Open in Claude Code (10 min)

**Option A: Claude Code (if you have it installed)**
```bash
# Open project in Claude Code
code-claude .  # or however you launch Claude Code

# In Claude Code, open chat and say:
"I'm building a thermal MCP server for data center cooling. 
I have a coldplate.py model that works. Help me wrap it in FastMCP.
Read my PROJECT_PLAN.md for context."
```

**Option B: Cowork (for file management)**
- Use Cowork to organize files
- Use Cowork to create folder structure
- Use me (this chat) for coding help!

---

## 🎯 CLAUDE CODE WORKFLOW - DAY BY DAY

### **Day 1 Prompt (Thermal Model Design)**

```
I'm building a thermal MCP server for GPU cold plate cooling.

Context:
- I'm a Staff Thermal Engineer with 4 years at Tesla
- Target: Data center liquid cooling (growing $6.6B market)
- Goal: Ship MVP in 7 days

I've created coldplate.py with basic 1D thermal resistance network.

Tasks for today:
1. Review my thermal model for accuracy
2. Add validation test cases
3. Suggest improvements for v1.0

Read src/models/coldplate.py and give me feedback.
```

---

### **Day 2 Prompt (Testing & Validation)**

```
Help me write comprehensive pytest tests for my ColdPlateModel.

Test cases needed:
1. Known validation case: 700W GPU, 12 LPM water → Tj should be 75-85°C
2. Edge cases: very low flow rate, very high power
3. Different coolants: water vs glycol vs dielectric
4. Optimization function: verify it finds minimum flow rate
5. Warning triggers: high temp, low flow, high pressure drop

Create tests/test_coldplate.py with at least 10 test cases.
Use pytest fixtures for common model configurations.
```

---

### **Day 3 Prompt (MCP Integration)**

```
Now let's wrap my thermal model in a FastMCP server.

Requirements:
1. Create src/mcp_server.py using FastMCP
2. Expose 3 tools:
   a) analyze_coldplate_system - basic analysis
   b) compare_cooling_options - compare coolants
   c) optimize_flow_rate - find optimal flow

3. Tool descriptions should be clear for Claude to understand when to use each

4. Include error handling for invalid inputs

Reference my coldplate.py model.
Show me the complete mcp_server.py implementation.
```

---

### **Day 4 Prompt (Documentation)**

```
Write a killer README.md for my GitHub repo.

Include:
- Compelling one-liner: "AI-powered thermal simulation for data center cooling"
- Why this exists (market opportunity)
- My background (Tesla thermal engineer)
- Installation instructions
- Usage examples (3 scenarios with Claude)
- Technical details (what it models)
- Roadmap (v0.2 features)
- Contributing guidelines
- License (MIT)

Make it professional but approachable.
Target audience: thermal engineers, data center architects, AI infrastructure teams.

Also create:
- examples/usage_examples.md - 3 detailed scenarios
- docs/model_details.md - technical documentation
```

---

### **Day 5 Prompt (Polish & Launch Prep)**

```
Code review time! Help me polish everything for launch.

Tasks:
1. Review all code for:
   - Error handling
   - Input validation
   - Code quality
   - Documentation
   - Performance

2. Add helpful error messages for common mistakes

3. Create a CHANGELOG.md starting with v0.1.0

4. Write 4 launch posts:
   - Reddit r/datacenter (technical, 400 words)
   - Hacker News Show HN (concise, 200 words)
   - Twitter/X thread (10 tweets)
   - LinkedIn post (professional, 500 words)

Include my background: Staff Thermal Engineer at Tesla, now exploring 
AI infrastructure. The data center cooling market is $6.6B growing 28% annually.
```

---

### **Day 6 Prompt (Launch Support)**

```
Today is launch day! Help me with:

1. Create a GitHub Actions workflow for:
   - Running tests on push
   - Code formatting check
   - Badge for README

2. Set up GitHub Sponsors with these tiers:
   $5/mo - Support development
   $25/mo - Priority features
   $99/mo - Commercial license
   $499/mo - Enterprise support

3. Write the MCP registry submission:
   - Name: thermal-mcp-server
   - Description: (write compelling 2-sentence description)
   - Categories: Engineering, Simulation, Data Center
   - Tags: thermal, cooling, data-center, gpu, ai-infrastructure

4. Final pre-launch checklist - what am I missing?
```

---

## 🔥 POWER TIPS FOR CLAUDE CODE

### **Tip 1: Reference Files Explicitly**
```
"Read src/models/coldplate.py and src/mcp_server.py.
Now refactor the error handling to be more robust."
```

### **Tip 2: Ask for Multiple Options**
```
"Show me 3 different ways to structure the MCP server tools:
1. Separate tool for each coolant type
2. Single tool with coolant as parameter
3. Hybrid approach

Which is best for user experience?"
```

### **Tip 3: Request Specific Formats**
```
"Create a test suite that:
- Uses pytest fixtures
- Has docstrings explaining each test
- Groups related tests in classes
- Includes parametrized tests for coolant types
- Outputs coverage report"
```

### **Tip 4: Iterative Refinement**
```
First: "Write basic MCP server wrapper"
Then: "Add input validation"
Then: "Add detailed error messages"
Then: "Add usage examples in docstrings"
```

### **Tip 5: Context Loading**
```
"Load PROJECT_PLAN.md. I'm on Day 3.
What should I focus on today?
Read my current code and suggest next steps."
```

---

## 📁 USING COWORK FOR PROJECT MANAGEMENT

### **Scenario 1: Organizing Research**

Use Cowork to:
- Create folder structure for docs
- Save market research PDFs
- Organize validation data
- Track competitor analysis

### **Scenario 2: Managing Examples**

Use Cowork to:
- Store example calculations
- Organize test cases
- Keep validation data
- Archive thermal property data

### **Scenario 3: Launch Materials**

Use Cowork to:
- Draft launch posts
- Save social media graphics
- Organize announcement emails
- Track launch metrics

---

## ⚡ DAILY WORKFLOW

### Morning (9am - Start Fresh)

1. **Open PROJECT_PLAN.md** - Review today's tasks
2. **Start Claude Code** - Load project
3. **First Prompt**: "What's my focus for Day X? Read PROJECT_PLAN.md"
4. **Work Session**: 2-3 hours of focused coding

### Afternoon (1pm - Build & Test)

1. **Test What You Built**: Run code, find issues
2. **Iterate with Claude Code**: "This isn't working, help me debug"
3. **Document as You Go**: Update docs, add comments

### Evening (Optional - Polish)

1. **Review Progress**: What worked? What's blocked?
2. **Prep Tomorrow**: Review next day's tasks
3. **Update PROJECT_PLAN.md**: Check off completed items

---

## 🚨 WHEN YOU GET STUCK

### Problem: "Thermal model seems wrong"

**Claude Code Prompt:**
```
My thermal calculations seem off. 

Test case: 700W GPU, 12 LPM water flow
Expected: Tj around 75-85°C
Getting: [your result]

Review my coldplate.py:
- Check thermal resistance values
- Verify heat transfer coefficient calculation
- Check pressure drop equations
- Are my assumptions reasonable?

I have 4 years of Tesla thermal experience - use engineering judgment.
```

---

### Problem: "MCP server not being called by Claude"

**Claude Code Prompt:**
```
My MCP server is installed but Claude isn't using it.

Current setup:
- Server starts without errors
- Tools are defined in mcp_server.py
- Claude Desktop config looks correct

Debug checklist:
1. Are tool descriptions clear?
2. Are parameter types correct?
3. Is server responding to requests?
4. How do I test tool invocation?

Show me how to debug this step by step.
```

---

### Problem: "Running out of time"

**Claude Code Prompt:**
```
It's Day X and I'm behind schedule.

What I've completed:
- [list what's done]

What's remaining:
- [list what's left]

Help me:
1. Identify what's essential for MVP
2. What can be cut for v0.2?
3. Fastest path to shippable product?

I need to launch in [X] days.
```

---

## 🎓 LEARNING RESOURCES

### FastMCP Documentation
- Read: https://github.com/jlowin/fastmcp
- Example: Look at existing MCP servers on registry

### Heat Transfer Review (if needed)
- Incropera & DeWitt basics
- Your Tesla simulation experience (best resource!)
- Textbook validation cases

### MCP Specification
- Official docs: https://modelcontextprotocol.io
- Discord: Join for community support

---

## ✅ SUCCESS CHECKLIST

Before launch, verify:

- [ ] Code runs without errors
- [ ] Tests pass (pytest)
- [ ] Claude can call your tools successfully
- [ ] README is complete and clear
- [ ] Examples work
- [ ] GitHub repo is public
- [ ] License file added (MIT)
- [ ] .gitignore is correct
- [ ] GitHub Sponsors enabled
- [ ] Launch posts drafted

---

## 🎉 YOU'VE GOT THIS!

**Remember:**
- You have 4 years of thermal expertise
- You know what "good enough" means
- MVP > Perfect
- Ship fast, iterate based on feedback

**Your advantage:**
- Only thermal engineer building this
- Tesla credibility
- Real expertise, not theoretical

**Next action:**
1. Copy the files I created
2. Open Claude Code
3. Start with Day 1 thermal model review
4. Message me if you get stuck!

**LET'S SHIP THIS! 🚀**

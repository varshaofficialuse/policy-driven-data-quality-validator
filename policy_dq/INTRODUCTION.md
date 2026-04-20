# Introduction to policy-dq

Hello! I am the owner of this project. Here is an overview of **policy-dq**, explained in simple English.

## 1. What is this project?
**policy-dq** is a tool that checks if your data (like CSV or JSON files) is "good" or "bad." It makes sure your data follows certain "business rules" (data contracts) before you use it in your systems.

## 2. How was it built?
It was built using modern Python tools:
- **Python 3.12+**: The main programming language.
- **uv**: A very fast tool to manage dependencies and the environment.
- **Pandas**: Used to load and process the data files quickly.
- **Pydantic**: Used to define the rules and check the data structure.
- **FastAPI**: Provides a web interface if you want to use it as a service.
- **Click**: Powers the command-line interface (CLI).

## 3. What are the possibilities with Kiro?
**Kiro** played a big part in building this project:
- **Spec-Driven Development**: We used Kiro to turn a written "Spec" (plan) into working code step-by-step.
- **Steering Files**: We used special files in `.kiro/steering/` to tell the AI assistant about the technical stack and quality standards we wanted.
- **Hooks**: We set up automated "hooks" that ran tests and checked for code style every time a file was changed.

## 4. What are the benefits?
- **Fast**: It uses a very fast engine to check data.
- **Flexible**: You can load rules from a local file or fetch them from a "Model Context Protocol" (MCP) server.
- **Clear Reports**: It creates both JSON (for computers) and Markdown (for people) reports.
- **CI/CD Ready**: It can be used in automated pipelines to stop "bad" data from being processed.

## 5. What is the workflow?
1. **Define Rules**: Create a YAML or JSON file with your validation rules (e.g., "Email must be required").
2. **Run Validation**: Use the CLI command `policy-dq validate data.csv --rules rules.yaml`.
3. **Review Report**: Check the console output or the generated report files to see any issues found.

## 6. Challenges and Issues
During development, we faced a few challenges:
- **In-memory Limits**: Since we use Pandas, very large files (several Gigabytes) might use a lot of RAM.
- **Rule Ordering**: We had to ensure that the errors found were always sorted the same way so that reports are consistent.
- **CLI Design**: We iterated on the CLI commands to make them as simple as possible for the user.

---
Created by the Project Owner.

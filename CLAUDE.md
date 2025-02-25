# CLAUDE.md - AWS IoT Monitoring System

## Build and Run Commands
- Run Streamlit app: `cd app && streamlit run app.py`
- Run IoT simulator: `python simulate_iot_data.py` or `python simulate_iot_data_v2.py`
- Terraform commands:
  - Initialize: `cd terraform && terraform init`
  - Plan: `cd terraform && terraform plan -var-file=production.tfvars -out=tfplan`
  - Apply: `cd terraform && terraform apply -auto-approve tfplan`

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports with a blank line between groups
- **Docstrings**: Use triple-quoted docstrings at the top of files and for all functions
- **Functions**: Use snake_case for function names; include descriptive docstrings
- **Variables**: Use snake_case; use descriptive names that indicate purpose
- **Error Handling**: Use try/except blocks with specific exception types and helpful error messages
- **Logging**: Use print statements for simple logging in scripts; include timestamps when relevant
- **Formatting**: Maintain consistent 4-space indentation
- **Type Hints**: No explicit type hints used; maintain consistency if adding them
- **Comments**: Add helpful comments for complex logic, especially in IoT simulation code
- **Constants**: Define constants at the top of files in UPPER_CASE

When modifying the codebase, follow existing patterns and maintain consistent style.
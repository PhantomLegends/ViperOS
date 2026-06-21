# ViperOS

ViperOS is a headless, local-first automation runtime designed for private on-device control. It provides a CLI and local HTTP API, with optional voice input and text-to-speech feedback, while keeping execution and storage on the local machine.

## Product Description

- Purpose: orchestrate local automation workflows through simple command-driven interactions.
- Runtime model: no cloud dependency, no GUI requirement, and cross-platform adapter-based execution.
- Control paths: CLI, local API requests, and optional voice-to-command input.
- Safety posture: local authentication, local persistence, and explicit confirmation objects for sensitive actions.

## File Layout

```text
ViperOS/
├─ README.md
├─ LICENSE
├─ config.yaml
├─ viper-os-core.plain
├─ template/
│  ├─ base.plain
│  └─ resources/
│     └─ run_unittests_python.ps1
└─ test_scripts/
   └─ run_unittests_python.ps1
```

### What Each File Represents

- `viper-os-core.plain`: main domain and functional specification for core behavior.
- `template/base.plain`: shared implementation constraints and baseline requirements.
- `config.yaml`: template/test script configuration values.
- `template/resources/run_unittests_python.ps1`: reference PowerShell test runner script template.
- `test_scripts/run_unittests_python.ps1`: project-level test runner used to execute isolated Python test runs.

## Overall Architecture

```mermaid
flowchart LR
	User[User / Operator] --> CLI[CLI Interface]
	User --> API[Local HTTP API]
	User --> Voice[Optional Voice Input]

	Voice --> Parser
	CLI --> Parser[Command Parser]
	API --> Parser

	Parser --> Engine[Workflow Engine]
	Engine --> Adapter[Hardware Adapter Layer]

	Adapter --> OS[Host OS Services]
	Engine --> DB[(SQLite Local State)]
	API --> DB

	Engine --> TTS[Optional TTS Engine]
	TTS --> User
```

## Dataflow Chart

```mermaid
flowchart TD
	A[Input: CLI / API / Voice] --> B[Normalize Command Text]
	B --> C[Parse Intent and Parameters]
	C --> D{Request Type}

	D -->|System Query| E[Read Runtime / Adapter Info]
	D -->|Command Execution| F[Route to Workflow Engine]
	D -->|Workflow Management| G[Create/List/Run Workflow]

	F --> H[Apply Failure Policy and Retries]
	H --> I[Execute via Hardware Adapter]

	G --> J[(Persist and Read in SQLite)]
	I --> K[(Log Command Outcome)]
	E --> K

	K --> L[Return Structured Result]
	L --> M[Optional Speech Feedback]
```

## User Interaction / Request Diagram

```mermaid
sequenceDiagram
	participant U as User
	participant C as CLI/API/Voice
	participant P as Command Parser
	participant W as Workflow Engine
	participant H as Hardware Adapter
	participant S as SQLite

	U->>C: Submit request
	C->>P: Forward command text
	P->>W: Dispatch parsed action

	alt Workflow or system action
		W->>H: Execute platform-safe operation
		H-->>W: Operation result
	end

	W->>S: Store logs / state changes
	S-->>W: Persistence confirmation
	W-->>C: Response payload
	C-->>U: Final result
```

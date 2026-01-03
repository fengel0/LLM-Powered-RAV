
# Prefect‑Core

**Prefect‑Core** is a lightweight Python package that extends the Prefect workflow orchestration framework.  
It provides core utilities, deployment helpers, and automation primitives that integrate directly with Prefect’s runtime.


## 📦 Installation

```bash
uv sync
```


---

## 🚀 Quick Start

```python
async def upload_files():
    logger.error("hi")


if __name__ == "__main__":
    flow = CustomFlow(upload_files)
    flow.add_automations(
        [
            Automation(
                name="test automation",
                trigger=EventTrigger(
                    expect={"test_lol"},
                    posture="Reactive",  # type: ignore
                    threshold=1,
                ),
                actions=[  # type: ignore
                    RunDeployment(  # type: ignore
                        deployment_id="d2386537-e8e2-457f-9e3e-2f82b7a5a109",
                        parameters={
                            "file_id": "{{ event.resource.id.split('/')[-1] }}"
                        },
                    )
                ],
            )
        ]
    )
    flow.serve(  # type: ignore
        name="Test Flow",
        tags=["file upload"],
    )
```




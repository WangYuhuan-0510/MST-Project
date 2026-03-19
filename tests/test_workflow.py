from mst.core.workflow import Pipeline, Workflow, WorkflowState


def test_workflow_pipeline_happy_path():
    calls: list[str] = []

    def step(name: str):
        def _fn(ctx: dict):
            calls.append(name)
            ctx = dict(ctx)
            ctx[name] = True
            return ctx

        return _fn

    wf = Workflow(
        pipeline=Pipeline(
            initialize=step("initialize"),
            acquire=step("acquire"),
            process=step("process"),
            fit=step("fit"),
            export=step("export"),
            ui_update=step("ui_update"),
        )
    )
    assert wf.state is WorkflowState.IDLE
    wf.start()
    assert wf.state is WorkflowState.INITIALIZING
    wf.run()
    assert wf.state is WorkflowState.FINISHED
    assert calls == ["initialize", "acquire", "process", "fit", "export", "ui_update"]
    assert wf.ctx["fit"] is True
    wf.reset()
    assert wf.state is WorkflowState.IDLE


def test_workflow_cancel():
    wf = Workflow()
    wf.start()
    assert wf.state is WorkflowState.INITIALIZING
    wf.cancel()
    wf.tick()
    assert wf.state is WorkflowState.CANCELLED


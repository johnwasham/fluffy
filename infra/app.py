#!/usr/bin/env python3
import aws_cdk as cdk
from fluffy_stack import FluffyStack

app = cdk.App()

FluffyStack(app, "FluffyStack")

app.synth()

#!/usr/bin/env python3
import aws_cdk as cdk
from fluffy_stack import FluffyStack

app = cdk.App()

# Adding the blog name allows your blog to coexist with other Fluffy blogs in your AWS account.
FluffyStack(app, "FluffyStack-YourBlog", blog_name="YourBlog")

app.synth()

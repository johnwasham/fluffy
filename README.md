<img src="readme-images/fluffy.svg" alt="fluffy logo" width="200"/>

# fluffy

Fluffy is the easiest way to write your blog locally, in simple markdown files, preview in your browser while writing, and then publish to Amazon S3. Your site is served via CloudFront to readers worldwide, with no scaling expertise required.

![fluffy UI](/readme-images/fluffy-screenshot.jpg)

## Requirements

- Python 3.10+
- Node.js (for AWS CDK CLI)
- An AWS account

## First-time setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/johnwasham/fluffy.git
cd fluffy
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

### 2. Configure your blog

Edit `blog/config.yaml`:

```yaml
title: My Blog
author: Your Name
base_url: https://yourdomain.com
disqus_shortname: your-disqus-shortname   # optional, remove if not using Disqus
cloudfront_distribution_id: CHANGE_ME     # fill in after CDK deploy (you can find it in CloudFront)
posts_per_page: 10
profile_image: /images/your_photo.jpg
bio: I short biography about you. Who are you? What are your hobbies?
hero_image: /images/hero_image.jpg (optional)
hero_subtitle: A subtitle to describe your blog's purpose
```

### 3. Set up AWS credentials

Copy the example env file and fill in your AWS credentials:

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1      # or whichever region you use
S3_BUCKET=                        # you'll fill this in after your CDK has deployed
```

The IAM user needs permissions for CloudFormation, S3, CloudFront, IAM to bootstrap and deploy. After the initial deploy, publishing only requires S3 and CloudFront permissions.

### 4. Deploy AWS infrastructure

```bash
npm install -g aws-cdk            # install CDK CLI
cd infra
pip3 install -r requirements.txt
export $(cat ../.env.local | xargs)
cdk bootstrap                     # first time only
cdk deploy
```

After deploy, copy the outputs into your config:
- **BucketName** → `S3_BUCKET` in `.env.local`  It starts with "fluffystack-blogbucket" and is followed by random letters and dashes
- **CloudFrontDistributionId** → You'll see this in the CloudFront dashboard. Add `cloudfront_distribution_id` in `blog/config.yaml`
- **CloudFrontDomain** → Find this in CloudFront (click on your new distribution). It looks like "DIGITS_AND_LETTERS.cloudfront.net". Point your DNS CNAME for your domain to this.

### 5. Build and publish

```bash
python3 src/builder.py    # generate static HTML into output/
python3 src/publisher.py  # upload to S3 and invalidate CloudFront
```

## Daily usage

Start the local editor:

```bash
source .venv/bin/activate
python3 src/server.py
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

- **Left pane** — write in Markdown; drag the divider to resize
- **Right pane** — live preview matching the published site
- **Save Draft** — saves locally with `status: draft` (not published)
- **Publish** — saves, builds, and uploads to S3 in one click
- `Cmd+S` / `Ctrl+S` — save draft

> **Note** When publishing via the editor, you don't need to run builder.py or publisher.py 😊

## Post format

Posts are stored as Markdown files in `blog/posts/YYYY/MM/slug.md` with YAML frontmatter:

```markdown
---
title: My Post Title
date: 2024-03-15
slug: my-post-title
status: published
feature_image: /images/header.jpg
disqus_id: my-post-title
tags: [startup, advice]
---

Post content here. Custom HTML blocks (YouTube embeds, tweets, etc.) are preserved as-is.
```

Setting `status: draft` excludes the post from builds and removes it from S3 on the next publish.

## Project structure

```
blog/posts/YYYY/MM/slug.md   markdown posts
blog/pages/                  static pages (about, etc.)
blog/images/                 header images and media
blog/config.yaml             blog settings (safe to commit)
theme/                       Jinja2 templates and CSS
src/                         Python application code
infra/                       AWS CDK stack
output/                      generated HTML — do not commit
.env.local                   AWS credentials — do not commit
```

## Debugging Style Changes

Run this if you're making stylesheet or template changes and want to see them locally:

```bash
python3 src/builder.py --local && cd output-local && python3 -m http.server 8000
```

"""
AWS CDK stack for Fluffy blog.

Creates:
  - S3 bucket configured for static website hosting
  - CloudFront distribution pointing to the S3 bucket

After deploying, point your DNS CNAME to the CloudFront domain printed in the outputs.

Deploy:
    cd infra
    pip install -r requirements.txt
    cdk bootstrap   # first time only
    cdk deploy
"""

import aws_cdk as cdk
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
import aws_cdk.aws_s3 as s3
from constructs import Construct


class FluffyStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for static site content
        bucket = s3.Bucket(
            self,
            "BlogBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            public_read_access=True,
            website_index_document="index.html",
            website_error_document="index.html",
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # Cache policy that includes query strings in the cache key so that
        # versioned URLs like style.css?v=abc123 are cached independently,
        # enabling cache busting without a CloudFront invalidation.
        cache_policy = cloudfront.CachePolicy(
            self,
            "BlogCachePolicy",
            cache_policy_name="Fluffy-QueryString-Cache",
            default_ttl=cdk.Duration.days(1),
            max_ttl=cdk.Duration.days(365),
            min_ttl=cdk.Duration.seconds(0),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            header_behavior=cloudfront.CacheHeaderBehavior.none(),
            cookie_behavior=cloudfront.CacheCookieBehavior.none(),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )

        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self,
            "BlogDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3StaticWebsiteOrigin(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cache_policy,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                compress=True,
            ),
            default_root_object="index.html",
            error_responses=[
                # Return index.html for 404s (supports clean URLs)
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            comment="Fluffy blog",
        )

        # Outputs
        cdk.CfnOutput(self, "BucketName", value=bucket.bucket_name)
        cdk.CfnOutput(
            self,
            "CloudFrontDomain",
            value=distribution.distribution_domain_name,
            description="Point your DNS CNAME to this domain",
        )
        cdk.CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="Add this to blog/config.yaml as cloudfront_distribution_id",
        )

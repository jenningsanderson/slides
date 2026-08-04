"""
Tests for slides_builder.config deploy/publish helpers.
"""

import pytest
from slides_builder.config import get_deploy_config, validate_deploy_config


class TestGetDeployConfig:
    def test_defaults_when_no_deploy_key(self):
        cfg = {}
        deploy = get_deploy_config(cfg)
        assert deploy["provider"] == "pages"
        assert deploy["path_prefix"] == ""
        assert deploy["s3"]["bucket"] == ""
        assert deploy["s3"]["region"] == "us-east-1"

    def test_provider_pages_explicit(self):
        cfg = {"deploy": {"provider": "pages"}}
        assert get_deploy_config(cfg)["provider"] == "pages"

    def test_provider_s3_explicit(self):
        cfg = {"deploy": {"provider": "s3", "s3": {"bucket": "my-bucket"}}}
        deploy = get_deploy_config(cfg)
        assert deploy["provider"] == "s3"
        assert deploy["s3"]["bucket"] == "my-bucket"

    def test_s3_defaults_merged(self):
        cfg = {"deploy": {"provider": "s3", "s3": {"bucket": "b"}}}
        s3 = get_deploy_config(cfg)["s3"]
        assert s3["region"] == "us-east-1"
        assert s3["cache_control_html"] == "no-cache"
        assert s3["cache_control_assets"] == "public,max-age=31536000,immutable"

    def test_s3_override_region(self):
        cfg = {"deploy": {"s3": {"bucket": "b", "region": "eu-west-1"}}}
        assert get_deploy_config(cfg)["s3"]["region"] == "eu-west-1"

    def test_path_prefix(self):
        cfg = {"deploy": {"path_prefix": "/my/path"}}
        assert get_deploy_config(cfg)["path_prefix"] == "/my/path"

    def test_deploy_not_dict_treated_as_empty(self):
        cfg = {"deploy": "invalid"}
        deploy = get_deploy_config(cfg)
        assert deploy["provider"] == "pages"

    def test_none_values_in_s3_use_defaults(self):
        cfg = {"deploy": {"s3": {"bucket": "b", "region": None}}}
        deploy = get_deploy_config(cfg)
        assert deploy["s3"]["region"] == "us-east-1"


class TestValidateDeployConfig:
    def test_pages_provider_valid(self):
        deploy = get_deploy_config({})
        assert validate_deploy_config(deploy) == []

    def test_s3_with_bucket_and_region_valid(self):
        cfg = {"deploy": {"provider": "s3", "s3": {"bucket": "b", "region": "us-east-1"}}}
        deploy = get_deploy_config(cfg)
        assert validate_deploy_config(deploy) == []

    def test_s3_missing_bucket_error(self):
        cfg = {"deploy": {"provider": "s3"}}
        deploy = get_deploy_config(cfg)
        errors = validate_deploy_config(deploy)
        assert any("bucket" in e for e in errors)

    def test_unknown_provider_error(self):
        deploy = {"provider": "ftp", "path_prefix": "", "s3": {}}
        errors = validate_deploy_config(deploy)
        assert any("provider" in e for e in errors)

    def test_s3_missing_region_error(self):
        deploy = {
            "provider": "s3",
            "path_prefix": "",
            "s3": {"bucket": "b", "region": ""},
        }
        errors = validate_deploy_config(deploy)
        assert any("region" in e for e in errors)

"""Unit tests for backend.utils.caching (ETag/Cache-Control utilities)."""

import pytest
from unittest.mock import MagicMock

from backend.utils.caching import (
    CacheConfig,
    generate_etag,
    build_cache_control_header,
    check_etag_match,
    add_cache_headers,
    create_cacheable_response,
    CacheInvalidator,
    get_cache_config_for_resource,
)


class TestGenerateEtag:
    def test_returns_quoted_string(self):
        etag = generate_etag({"id": "1"})
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_same_data_same_etag(self):
        data = {"id": "123", "name": "Test"}
        assert generate_etag(data) == generate_etag(data)

    def test_different_data_different_etag(self):
        assert generate_etag({"id": "1"}) != generate_etag({"id": "2"})

    def test_order_independent(self):
        # sort_keys=True means order doesn't matter
        a = generate_etag({"b": 2, "a": 1})
        b = generate_etag({"a": 1, "b": 2})
        assert a == b

    def test_list_data(self):
        etag = generate_etag([1, 2, 3])
        assert len(etag) > 2

    def test_empty_dict(self):
        etag = generate_etag({})
        assert etag.startswith('"')


class TestBuildCacheControlHeader:
    def test_no_cache_directive(self):
        result = build_cache_control_header({"no_cache": True})
        assert "no-cache" in result

    def test_no_store_directive(self):
        result = build_cache_control_header({"no_store": True})
        assert "no-store" in result

    def test_max_age(self):
        result = build_cache_control_header({"max_age": 300})
        assert "max-age=300" in result

    def test_private(self):
        result = build_cache_control_header({"private": True})
        assert "private" in result

    def test_public_not_added_when_private_set(self):
        result = build_cache_control_header({"private": True, "public": True})
        assert "public" not in result

    def test_stale_while_revalidate(self):
        result = build_cache_control_header({"stale_while_revalidate": 600})
        assert "stale-while-revalidate=600" in result

    def test_multiple_directives(self):
        result = build_cache_control_header(
            {
                "max_age": 300,
                "stale_while_revalidate": 600,
            }
        )
        assert "max-age=300" in result
        assert "stale-while-revalidate=600" in result

    def test_empty_config_returns_empty_string(self):
        result = build_cache_control_header({})
        assert result == ""

    def test_real_time_config(self):
        result = build_cache_control_header(CacheConfig.REAL_TIME)
        assert "no-cache" in result
        assert "no-store" in result

    def test_posts_config(self):
        result = build_cache_control_header(CacheConfig.POSTS)
        assert "max-age=300" in result


class TestCheckEtagMatch:
    def _make_request(self, if_none_match=None):
        req = MagicMock()
        req.headers = {}
        if if_none_match:
            req.headers["If-None-Match"] = if_none_match
        return req

    def test_matching_etag_returns_true(self):
        req = self._make_request('"abc123"')
        assert check_etag_match(req, '"abc123"') is True

    def test_non_matching_etag_returns_false(self):
        req = self._make_request('"abc123"')
        assert check_etag_match(req, '"xyz789"') is False

    def test_no_header_returns_false(self):
        req = self._make_request()
        assert check_etag_match(req, '"abc123"') is False

    def test_multiple_etags_matches_one(self):
        req = self._make_request('"old1", "abc123", "old2"')
        assert check_etag_match(req, '"abc123"') is True


class TestAddCacheHeaders:
    def test_adds_cache_control_header(self):
        from fastapi.responses import JSONResponse

        resp = JSONResponse(content={})
        add_cache_headers(resp, {"max_age": 300})
        assert "Cache-Control" in resp.headers
        assert "max-age=300" in resp.headers["Cache-Control"]

    def test_adds_etag_header(self):
        from fastapi.responses import JSONResponse

        resp = JSONResponse(content={})
        add_cache_headers(resp, {}, etag='"abc123"')
        assert resp.headers["ETag"] == '"abc123"'

    def test_adds_vary_header(self):
        from fastapi.responses import JSONResponse

        resp = JSONResponse(content={})
        add_cache_headers(resp, {})
        assert "Vary" in resp.headers


class TestCreateCacheableResponse:
    def _make_request(self, if_none_match=None):
        req = MagicMock()
        req.headers = {}
        if if_none_match:
            req.headers["If-None-Match"] = if_none_match
        return req

    def test_returns_200_on_cache_miss(self):
        req = self._make_request()
        resp = create_cacheable_response({"id": "1"}, CacheConfig.POSTS, req)
        assert resp.status_code == 200

    def test_returns_304_on_cache_hit(self):
        data = {"id": "1"}
        etag = generate_etag(data)
        req = self._make_request(if_none_match=etag)
        resp = create_cacheable_response(data, CacheConfig.POSTS, req)
        assert resp.status_code == 304

    def test_full_response_has_etag(self):
        req = self._make_request()
        resp = create_cacheable_response({"id": "1"}, CacheConfig.POSTS, req)
        assert "ETag" in resp.headers


class TestCacheInvalidator:
    def test_returns_invalidation_header(self):
        headers = CacheInvalidator.get_invalidation_header(["posts", "projects"])
        assert "X-Cache-Invalidate" in headers
        assert "posts" in headers["X-Cache-Invalidate"]
        assert "projects" in headers["X-Cache-Invalidate"]

    def test_includes_timestamp(self):
        headers = CacheInvalidator.get_invalidation_header(["posts"])
        assert "X-Cache-Timestamp" in headers


class TestGetCacheConfigForResource:
    def test_posts_returns_posts_config(self):
        assert get_cache_config_for_resource("posts") == CacheConfig.POSTS

    def test_clients_returns_clients_config(self):
        assert get_cache_config_for_resource("clients") == CacheConfig.CLIENTS

    def test_unknown_returns_default(self):
        result = get_cache_config_for_resource("unknown")
        assert result == CacheConfig.POSTS  # documented default

    def test_templates_config(self):
        assert get_cache_config_for_resource("templates") == CacheConfig.TEMPLATES

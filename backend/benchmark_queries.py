#!/usr/bin/env python3
"""
Benchmark script to measure query performance improvements.

This script tests query performance before and after optimizations:
- N+1 query problem (eager loading)
- Composite indexes
- Various filter combinations

Usage:
    python benchmark_queries.py
"""
import sys
import time
from pathlib import Path
from typing import Callable, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database import SessionLocal
from backend.models import Post, Project, Client
from backend.services import crud
from sqlalchemy import event
from sqlalchemy.engine import Engine


# Track query count
query_count = 0


@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Count all SQL queries"""
    global query_count
    query_count += 1


def reset_query_count():
    """Reset query counter"""
    global query_count
    query_count = 0


def benchmark_function(name: str, func: Callable, iterations: int = 10) -> dict:
    """
    Benchmark a function and return performance metrics.

    Args:
        name: Benchmark name
        func: Function to benchmark
        iterations: Number of iterations to run

    Returns:
        Dict with timing and query count stats
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {name}")
    print(f"{'='*60}")

    times = []
    query_counts = []

    for i in range(iterations):
        reset_query_count()
        start = time.time()

        try:
            func()
            elapsed = (time.time() - start) * 1000  # Convert to ms

            times.append(elapsed)
            query_counts.append(query_count)

            print(f"  Run {i+1}/{iterations}: {elapsed:.2f}ms, {query_count} queries")

        except Exception as e:
            print(f"  Run {i+1}/{iterations}: ERROR - {e}")

    if not times:
        return {"error": "All runs failed"}

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    avg_queries = sum(query_counts) / len(query_counts)

    print(f"\nResults:")
    print(f"  Average time: {avg_time:.2f}ms")
    print(f"  Min time: {min_time:.2f}ms")
    print(f"  Max time: {max_time:.2f}ms")
    print(f"  Average queries: {avg_queries:.1f}")

    return {
        "name": name,
        "avg_time_ms": avg_time,
        "min_time_ms": min_time,
        "max_time_ms": max_time,
        "avg_queries": avg_queries,
    }


def benchmark_get_posts_basic():
    """Benchmark basic get_posts query"""
    def run():
        db = SessionLocal()
        try:
            posts = crud.get_posts(db, limit=100)
            # Access relationships to trigger lazy loading (if not eager loaded)
            for post in posts:
                if post.project:
                    _ = post.project.name
                if post.run:
                    _ = post.run.status
            return len(posts)
        finally:
            db.close()

    return benchmark_function("get_posts (basic, 100 posts)", run)


def benchmark_get_posts_filtered():
    """Benchmark filtered get_posts query"""
    def run():
        db = SessionLocal()
        try:
            posts = crud.get_posts(db, status="approved", limit=100)
            for post in posts:
                if post.project:
                    _ = post.project.name
            return len(posts)
        finally:
            db.close()

    return benchmark_function("get_posts (status filter)", run)


def benchmark_get_posts_complex_filter():
    """Benchmark complex filtered get_posts query"""
    def run():
        db = SessionLocal()
        try:
            posts = crud.get_posts(
                db,
                status="approved",
                platform="linkedin",
                min_word_count=100,
                max_word_count=300,
                limit=100
            )
            for post in posts:
                if post.project:
                    _ = post.project.name
            return len(posts)
        finally:
            db.close()

    return benchmark_function("get_posts (complex filters)", run)


def benchmark_get_posts_search():
    """Benchmark text search query"""
    def run():
        db = SessionLocal()
        try:
            posts = crud.get_posts(db, search="marketing", limit=100)
            return len(posts)
        finally:
            db.close()

    return benchmark_function("get_posts (text search)", run)


def benchmark_get_projects():
    """Benchmark get_projects query"""
    def run():
        db = SessionLocal()
        try:
            projects = crud.get_projects(db, limit=50)
            # Access client relationship
            for project in projects:
                if project.client:
                    _ = project.client.name
            return len(projects)
        finally:
            db.close()

    return benchmark_function("get_projects (with client relationship)", run)


def create_test_data(db):
    """Create test data for benchmarking"""
    print("\nChecking for test data...")

    # Check if we have enough data
    post_count = db.query(Post).count()
    project_count = db.query(Project).count()
    client_count = db.query(Client).count()

    print(f"  Posts: {post_count}")
    print(f"  Projects: {project_count}")
    print(f"  Clients: {client_count}")

    if post_count < 100:
        print(f"\n⚠️  Warning: Only {post_count} posts found.")
        print("  For accurate benchmarks, you should have at least 100 posts.")
        print("  Run content generation to create more posts.")
        print()
        response = input("Continue with limited data? (yes/no): ")
        if response.lower() != 'yes':
            return False

    return True


def print_summary(results: List[dict]):
    """Print benchmark summary"""
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print()
    print(f"{'Benchmark':<40} {'Avg Time':>10} {'Queries':>8}")
    print("-"*60)

    for result in results:
        if "error" not in result:
            print(f"{result['name']:<40} {result['avg_time_ms']:>9.2f}ms {result['avg_queries']:>7.1f}")

    print()
    print("Performance Analysis:")
    print("  ✓ Good: <50ms response time, <5 queries")
    print("  ⚠️  Moderate: 50-200ms response time, 5-20 queries")
    print("  ✗ Poor: >200ms response time, >20 queries")
    print()
    print("N+1 Problem Check:")
    print("  - If 'Queries' count is high (>10 for 100 posts), eager loading may not be working")
    print("  - Expected: 1-3 queries total (1 for posts, 1-2 for joins)")
    print()


def main():
    """Main benchmark runner"""
    print("="*60)
    print("DATABASE QUERY PERFORMANCE BENCHMARK")
    print("="*60)
    print()
    print("This script measures query performance with optimizations:")
    print("  - Eager loading (joinedload)")
    print("  - Composite indexes")
    print("  - Various filter combinations")
    print()

    db = SessionLocal()
    try:
        # Check test data
        if not create_test_data(db):
            return

        # Run benchmarks
        results = []

        results.append(benchmark_get_posts_basic())
        results.append(benchmark_get_posts_filtered())
        results.append(benchmark_get_posts_complex_filter())
        results.append(benchmark_get_posts_search())
        results.append(benchmark_get_projects())

        # Print summary
        print_summary(results)

    finally:
        db.close()

    print("="*60)
    print("Benchmark complete!")
    print("="*60)


if __name__ == "__main__":
    main()

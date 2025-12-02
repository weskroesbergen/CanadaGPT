"""Schema validation logic for comparing Neo4j against GraphQL definitions."""

import re
from typing import Dict, List, Any


def extract_graphql_schema_elements(schema_path: str) -> Dict[str, Any]:
    """Extract node labels and relationship types from GraphQL schema file."""
    try:
        with open(schema_path, 'r') as f:
            content = f.read()

        # Extract type definitions (node labels)
        type_pattern = r'type\s+(\w+)\s+@node'
        node_labels = re.findall(type_pattern, content)

        # Extract relationship patterns from @relationship directives
        rel_pattern = r'@relationship\(.*?type:\s*"(\w+)"'
        relationship_types = list(set(re.findall(rel_pattern, content)))

        return {
            "node_labels": sorted(node_labels),
            "relationship_types": sorted(relationship_types),
            "total_types": len(node_labels),
            "total_relationships": len(relationship_types)
        }
    except Exception as e:
        return {
            "error": f"Failed to parse GraphQL schema: {str(e)}",
            "node_labels": [],
            "relationship_types": []
        }


def get_neo4j_schema(driver, database: str) -> Dict[str, Any]:
    """Query Neo4j for actual schema (labels and relationship types)."""
    try:
        with driver.session(database=database) as session:
            # Get node labels
            labels_result = session.run("CALL db.labels()")
            node_labels = sorted([record[0] for record in labels_result])

            # Get relationship types
            rels_result = session.run("CALL db.relationshipTypes()")
            relationship_types = sorted([record[0] for record in rels_result])

            # Get indexes
            indexes_result = session.run("SHOW INDEXES")
            indexes = [dict(record) for record in indexes_result]

            # Get constraints
            constraints_result = session.run("SHOW CONSTRAINTS")
            constraints = [dict(record) for record in constraints_result]

            return {
                "node_labels": node_labels,
                "relationship_types": relationship_types,
                "indexes": indexes,
                "constraints": constraints,
                "total_labels": len(node_labels),
                "total_rel_types": len(relationship_types)
            }
    except Exception as e:
        return {
            "error": f"Failed to query Neo4j schema: {str(e)}",
            "node_labels": [],
            "relationship_types": [],
            "indexes": [],
            "constraints": []
        }


def compare_schemas(graphql_schema: Dict, neo4j_schema: Dict) -> Dict[str, Any]:
    """Compare GraphQL expected schema with actual Neo4j schema."""
    # Node label comparison
    expected_labels = set(graphql_schema.get("node_labels", []))
    actual_labels = set(neo4j_schema.get("node_labels", []))

    missing_labels = expected_labels - actual_labels
    extra_labels = actual_labels - expected_labels

    # Relationship type comparison
    expected_rels = set(graphql_schema.get("relationship_types", []))
    actual_rels = set(neo4j_schema.get("relationship_types", []))

    missing_rels = expected_rels - actual_rels
    extra_rels = actual_rels - expected_rels

    # Calculate match percentage
    label_match_pct = (len(expected_labels & actual_labels) / len(expected_labels) * 100) if expected_labels else 0
    rel_match_pct = (len(expected_rels & actual_rels) / len(expected_rels) * 100) if expected_rels else 0

    return {
        "node_labels": {
            "expected": sorted(list(expected_labels)),
            "actual": sorted(list(actual_labels)),
            "missing": sorted(list(missing_labels)),
            "extra": sorted(list(extra_labels)),
            "match_percentage": round(label_match_pct, 1)
        },
        "relationship_types": {
            "expected": sorted(list(expected_rels)),
            "actual": sorted(list(actual_rels)),
            "missing": sorted(list(missing_rels)),
            "extra": sorted(list(extra_rels)),
            "match_percentage": round(rel_match_pct, 1)
        },
        "indexes": neo4j_schema.get("indexes", []),
        "constraints": neo4j_schema.get("constraints", []),
        "overall_status": "valid" if not missing_labels and not missing_rels else "invalid"
    }


def find_orphaned_nodes(driver, database: str) -> List[Dict[str, Any]]:
    """Find nodes with no relationships (potential data quality issues)."""
    try:
        with driver.session(database=database) as session:
            query = """
            MATCH (n)
            WHERE NOT (n)--()
            WITH labels(n) as node_labels, count(*) as orphan_count
            RETURN node_labels, orphan_count
            ORDER BY orphan_count DESC
            """
            result = session.run(query)
            return [dict(record) for record in result]
    except Exception as e:
        return [{"error": str(e)}]


def validate_schema_against_graphql(driver, schema_path: str, database: str) -> Dict[str, Any]:
    """
    Main validation function: compare Neo4j schema against GraphQL definitions.

    Returns a comprehensive validation report.
    """
    # Extract expected schema from GraphQL
    graphql_schema = extract_graphql_schema_elements(schema_path)
    if "error" in graphql_schema:
        return graphql_schema

    # Get actual Neo4j schema
    neo4j_schema = get_neo4j_schema(driver, database)
    if "error" in neo4j_schema:
        return neo4j_schema

    # Compare schemas
    comparison = compare_schemas(graphql_schema, neo4j_schema)

    # Find orphaned nodes (data quality check)
    orphaned_nodes = find_orphaned_nodes(driver, database)

    # Build comprehensive report
    report = {
        "graphql_schema_path": schema_path,
        "neo4j_database": database,
        "validation_status": comparison["overall_status"],
        "node_labels": comparison["node_labels"],
        "relationship_types": comparison["relationship_types"],
        "indexes": {
            "total": len(comparison["indexes"]),
            "details": comparison["indexes"]
        },
        "constraints": {
            "total": len(comparison["constraints"]),
            "details": comparison["constraints"]
        },
        "data_quality": {
            "orphaned_nodes": orphaned_nodes
        },
        "recommendations": []
    }

    # Add recommendations
    if comparison["node_labels"]["missing"]:
        report["recommendations"].append(
            f"Missing node labels in Neo4j: {', '.join(comparison['node_labels']['missing'])}. "
            "Consider running data ingestion or updating GraphQL schema."
        )

    if comparison["relationship_types"]["missing"]:
        report["recommendations"].append(
            f"Missing relationship types in Neo4j: {', '.join(comparison['relationship_types']['missing'])}. "
            "Check if relationships are being created correctly during ingestion."
        )

    if orphaned_nodes:
        total_orphans = sum(node.get("orphan_count", 0) for node in orphaned_nodes if "orphan_count" in node)
        report["recommendations"].append(
            f"Found {total_orphans} orphaned nodes across {len(orphaned_nodes)} label types. "
            "Review data pipeline for relationship creation."
        )

    if not report["recommendations"]:
        report["recommendations"].append("Schema validation passed! No issues detected.")

    return report

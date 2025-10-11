# Feature files for BDD testing
# This directory contains Gherkin feature files for the Context Relay System

from pytest_bdd import scenario

# Load feature scenarios
context_initialization_feature = scenario("context_initialization.feature", "Successful context initialization with minimal data")
context_initialization_feature_complex = scenario("context_initialization.feature", "Context initialization with complex initial input")
context_initialization_feature_failure = scenario("context_initialization.feature", "Context initialization failure due to invalid input")

# Create generic aliases for import compatibility
context_merging_feature = scenario("context_merging.feature", "Successful union merge of two contexts")
context_merging_feature_union = scenario("context_merging.feature", "Successful union merge of two contexts")
context_merging_feature_nonexistent = scenario("context_merging.feature", "Merge with one or more non-existent contexts")

# Create generic aliases for import compatibility
context_pruning_feature = scenario("context_pruning.feature", "Successful pruning by recency strategy")
context_pruning_feature_recency = scenario("context_pruning.feature", "Successful pruning by recency strategy")
context_pruning_feature_insufficient = scenario("context_pruning.feature", "Pruning fails due to insufficient context")
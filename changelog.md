## version 1.5.0
1. Feature: add @config and update autowire;
2. Feature: rename add_mod_ctx to add_config_ctx.

## version 1.4.0
1. Feature: support data type UUID for the request parameters.
2. Feature: optimize endpoint name compatibility check.

## version 1.3.0
1. Deprecated: `getdoc()`;
2. Feature: support app['lessweb.routes'];
3. Feature: support multiple positional-only parameters;
4. Feature: add e2e test (new tests/e2e/ dir);
5. Feature: when incorrectly used, raise TypeError as the standard specification;
6. Feature: add autopep8 linter;
7. Feature: assert endpoint name compatible with method-path;
8. Feature: Route add member: endpoint;

## version 1.2.0
1. Feature: support typecasting Union and NewType;

## version 1.1.0
1. Feature: add unittest (new tests/ dir);
2. Feature: add mypy test;
4. Feature: add Github Action;
3. Feature: support typecasting Literal;

## version 1.0.8

1. Featuer: add changlog.md;
2. Fix bug: response serialization does not support dataclass;
3. Feature: change setup.py into pyproject.toml;

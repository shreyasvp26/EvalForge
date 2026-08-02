"""Infrastructure contracts owned by the Application Layer.

Domain already defines repository Protocols. Application adds contracts for
concerns that are use-case-scoped rather than aggregate-scoped: Unit of Work,
domain event dispatch, run enqueueing, authorization, and idempotency.

Infrastructure implements these; Application never imports concrete infra.
"""

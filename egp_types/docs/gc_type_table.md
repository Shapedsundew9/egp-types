# GC Type Flows

```mermaid
flowchart TD
    %% Shows the paths for GC type conversions in EGP
    %% NOTE aGC is not necessarily a complete type for purpose
    A[JSON] --> B1[eGC]
    B1 --> |Derived| B2[aGC]
    A --> B2
    B2 --> |Consistency Check| C[Genomic Library]
    C --> D[aGC]
    D --> |Derived| E[gGC]
    E --> |Consistency Check| F[Gene Pool]
    subgraph Gene Pool Cache
        direction TB
        G[Genetic Code]
    end
    F --> G
    G --> H[dGC]
    H --> G
    I[eGC] --> |Conversion| J[dGC]
    J --> |Consistency Check| G
    G --> K[gGC]
    K --> |Consistency Check| F
    F --> |Consistency Check| C
```

# Transformations

Column header types can be converted row types where there is an **X**

|     | eGC | dGC | gGC | GC | aGC |
|-----|-----|-----|-----|----|-----|
| eGC |  X  |     |     |    |     |
| dGC |  X  |  X  |     |  X |     |
| gGC |     |     |  X  |  X |  X  |
| GC  |     |  X  |  X  |  X |     |
| aGC |  X  |     |     |    |  X  |
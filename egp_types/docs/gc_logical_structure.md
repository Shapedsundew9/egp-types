# Genetric Code Logical Structure
A genetic codes, GC, is a recursively embedded structure. A GC may have none, one or two embedded GCs that are connected as a graph. The GC graph is deswcribed in ... A GC with no embedded GCs is called a codon. Codons represent a functional primitive.
```mermaid
flowchart TB
    subgraph Codon GC
    end
```
Embedded GCs are identified as A or B. The diagram below shows a GC with a GC A and a GC B both of which are codons.
```mermaid
flowchart TB
    subgraph GC
        subgraph Codon A
        end
        subgraph Codon B
        end
    end
```
GCs can be infinitely embedded. The diagram below shows four levels of embedding.
```mermaid
flowchart TB
	subgraph Top Level GC
		direction TB
		subgraph A
			direction TB
			subgraph AA
				direction TB
				subgraph AAA
					direction TB
					subgraph AAAA
						direction TB
					end
					subgraph AAAB
						direction TB
					end
				end
				subgraph AAB
					direction TB
					subgraph AABA
						direction TB
					end
					subgraph AABB
						direction TB
					end
				end
			end
			subgraph AB
				direction TB
				subgraph ABA
					direction TB
					subgraph ABAA
						direction TB
					end
					subgraph ABAB
						direction TB
					end
				end
				subgraph ABB
					direction TB
					subgraph ABBA
						direction TB
					end
					subgraph ABBB
						direction TB
					end
				end
			end
		end
		subgraph B
			direction TB
			subgraph BA
				direction TB
				subgraph BAA
					direction TB
					subgraph BAAA
						direction TB
					end
					subgraph BAAB
						direction TB
					end
				end
				subgraph BAB
					direction TB
					subgraph BABA
						direction TB
					end
					subgraph BABB
						direction TB
					end
				end
			end
			subgraph BB
				direction TB
				subgraph BBA
					direction TB
					subgraph BBAA
						direction TB
					end
					subgraph BBAB
						direction TB
					end
				end
				subgraph BBB
					direction TB
					subgraph BBBA
						direction TB
					end
					subgraph BBBB
						direction TB
					end
				end
			end
		end
	end
```
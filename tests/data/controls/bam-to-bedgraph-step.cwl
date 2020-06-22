class: Workflow
requirements:
- class: StepInputExpressionRequirement
- class: InlineJavascriptRequirement
inputs:
- type:
  - 'null'
  - boolean
  doc: "Change strand af the mate read, so both reads come from the same strand"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#dutp
- type:
  - 'null'
  - int
  doc: "Set fixed fragment size for genome coverage calculation"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#fragment_size
- type: File
  doc: "Input BAM file, sorted by coordinates"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_file
- type:
  - 'null'
  - int
  doc: |
    Parameter to calculate scale as 1000000/mapped_reads_number. Ignored by bedtools-genomecov.cwl in
    bam_to_bedgraph step if scale is provided
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#mapped_reads_number
- type:
  - 'null'
  - string
  doc: "Output filename for generated bedGraph"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename
- type:
  - 'null'
  - boolean
  doc: "Enable paired-end genome coverage calculation"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#pairchip
- type:
  - 'null'
  - float
  doc: "Coefficient to scale the genome coverage by a constant factor"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#scale
- type:
  - 'null'
  - boolean
  doc: "Calculate genome coverage for each part of the splitted by 'N' and 'D' read"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#split
- type:
  - 'null'
  - string
  doc: "Calculate genome coverage of intervals from a specific strand"
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#strand
outputs:
- id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/genome_coverage_file
  type: File
  outputSource: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/genome_coverage_file
steps:
- run: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/tools/bedtools-genomecov.cwl
  in:
  - default: "-bg"
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/depth
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#dutp
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/du
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#fragment_size
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/fragment_size
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_file
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/input_file
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#mapped_reads_number
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/mapped_reads_number
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/output_filename
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#pairchip
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/pairchip
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#scale
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/scale
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#split
    valueFrom: |
      ${
        if (self == null){
          return true;
        } else {
          return self;
        }
      }
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/split
  - source: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#strand
    id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/strand
  out: [file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph/genome_coverage_file]
  id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bam_to_bedgraph
$namespaces:
  s: http://schema.org/
$schemas:
- https://schema.org/version/latest/schema.rdf

doc: |-
  Workflow converts input BAM file into bigWig and bedGraph files.

  Input BAM file should be sorted by coordinates (required by `bam_to_bedgraph` step).

  If `split` input is not provided use true by default. Default logic is implemented in `valueFrom` field of `split`
  input inside `bam_to_bedgraph` step to avoid possible bug in cwltool with setting default values for workflow inputs.

  `scale` has higher priority over the `mapped_reads_number`. The last one is used to calculate `-scale` parameter for
  `bedtools genomecov` (step `bam_to_bedgraph`) only in a case when input `scale` is not provided. All logic is
  implemented inside `bedtools-genomecov.cwl`.

  `bigwig_filename` defines the output name only for generated bigWig file. `bedgraph_filename` defines the output name
  for generated bedGraph file and can influence on generated bigWig filename in case when `bigwig_filename` is not provided.

  All workflow inputs and outputs don't have `format` field to avoid format incompatibility errors when workflow is used
  as subworkflow.
id: file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl
http://schema.org/name: "bam-bedgraph-bigwig"
http://schema.org/downloadUrl: https://raw.githubusercontent.com/Barski-lab/workflows/master/tools/bam-bedgraph-bigwig.cwl
http://schema.org/codeRepository: https://github.com/Barski-lab/workflows
http://schema.org/license: http://www.apache.org/licenses/LICENSE-2.0
http://schema.org/isPartOf:
  class: http://schema.org/CreativeWork
  http://schema.org/name: Common Workflow Language
  http://schema.org/url: http://commonwl.org/
http://schema.org/creator:
- class: http://schema.org/Organization
  http://schema.org/legalName: "Cincinnati Children's Hospital Medical Center"
  http://schema.org/location:
  - class: http://schema.org/PostalAddress
    http://schema.org/addressCountry: "USA"
    http://schema.org/addressLocality: "Cincinnati"
    http://schema.org/addressRegion: "OH"
    http://schema.org/postalCode: "45229"
    http://schema.org/streetAddress: "3333 Burnet Ave"
    http://schema.org/telephone: "+1(513)636-4200"
  http://schema.org/logo: "https://www.cincinnatichildrens.org/-/media/cincinnati%20childrens/global%20shared/childrens-logo-new.png"
  http://schema.org/department:
  - class: http://schema.org/Organization
    http://schema.org/legalName: "Allergy and Immunology"
    http://schema.org/department:
    - class: http://schema.org/Organization
      http://schema.org/legalName: "Barski Research Lab"
      http://schema.org/member:
      - class: http://schema.org/Person
        http://schema.org/name: Michael Kotliar
        http://schema.org/email: mailto:misha.kotliar@gmail.com
        http://schema.org/sameAs:
        - id: http://orcid.org/0000-0002-6486-3898
hints:
- class: LoadListingRequirement
  loadListing: deep_listing
- class: NetworkAccess
  networkAccess: true
cwlVersion: v1.2.0-dev3
http://commonwl.org/cwltool#original_cwlVersion: v1.0
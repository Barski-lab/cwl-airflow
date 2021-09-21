cwlVersion: v1.2.0-dev4
class: Workflow


requirements:
  - class: StepInputExpressionRequirement
  - class: InlineJavascriptRequirement


inputs:

  bam_file:
    type: File
    doc: "Input BAM file, sorted by coordinates"

  chrom_length_file:
    type: File
    doc: "Tab delimited chromosome length file: <chromName><TAB><chromSize>"

  scale:
    type: float?
    doc: "Coefficient to scale the genome coverage by a constant factor"

  mapped_reads_number:
    type: int?
    doc: |
      Parameter to calculate scale as 1000000/mapped_reads_number. Ignored by bedtools-genomecov.cwl in
      bam_to_bedgraph step if scale is provided

  sort_bedgraph:
    type: boolean?
    doc: "Sort bedGraph file"

  pairchip:
    type: boolean?
    doc: "Enable paired-end genome coverage calculation"

  fragment_size:
    type: int?
    doc: "Set fixed fragment size for genome coverage calculation"

  strand:
    type: string?
    doc: "Calculate genome coverage of intervals from a specific strand"

  bigwig_filename:
    type: string?
    doc: "Output filename for generated bigWig"

  bedgraph_filename:
    type: string?
    doc: "Output filename for generated bedGraph"

  split:
    type: boolean?
    doc: "Calculate genome coverage for each part of the splitted by 'N' and 'D' read"

  dutp:
    type: boolean?
    doc: "Change strand af the mate read, so both reads come from the same strand"


outputs:

  bigwig_file:
    type: File
    outputSource: sorted_bedgraph_to_bigwig/bigwig_file
    doc: "Output bigWig file"

  bedgraph_file:
    type: File
    outputSource: sort_bedgraph/sorted_file
    label: "bedGraph output file"
    doc: "Output bedGraph file"


steps:

  bam_to_bedgraph:
    run: ../tools/bedtools-genomecov.cwl
    in:
      input_file: bam_file
      depth:
        default: "-bg"
      split:
        source: split
        valueFrom: |
          ${
            if (self == null){
              return true;
            } else {
              return self;
            }
          }
      output_filename: bedgraph_filename
      pairchip: pairchip
      fragment_size: fragment_size
      scale: scale
      mapped_reads_number: mapped_reads_number
      strand: strand
      du: dutp
    out: [genome_coverage_file]

  sort_bedgraph:
    run: ../tools/linux-sort.cwl
    in:
      unsorted_file: bam_to_bedgraph/genome_coverage_file
      sort_bedgraph: sort_bedgraph
      key:
        default: ["1,1","2,2n"]
    when: $(inputs.sort_bedgraph)
    out: [sorted_file]

  sorted_bedgraph_to_bigwig:
    run: ../tools/ucsc-bedgraphtobigwig.cwl
    in:
      bedgraph_file: sort_bedgraph/sorted_file
      chrom_length_file: chrom_length_file
      output_filename: bigwig_filename
    out: [bigwig_file]


$namespaces:
  s: http://schema.org/

$schemas:
- https://github.com/schemaorg/schemaorg/raw/main/data/releases/11.01/schemaorg-current-http.rdf

s:name: "bam-bedgraph-bigwig"
s:downloadUrl: https://raw.githubusercontent.com/Barski-lab/workflows/master/tools/bam-bedgraph-bigwig.cwl
s:codeRepository: https://github.com/Barski-lab/workflows
s:license: http://www.apache.org/licenses/LICENSE-2.0

s:isPartOf:
  class: s:CreativeWork
  s:name: Common Workflow Language
  s:url: http://commonwl.org/

s:creator:
- class: s:Organization
  s:legalName: "Cincinnati Children's Hospital Medical Center"
  s:location:
  - class: s:PostalAddress
    s:addressCountry: "USA"
    s:addressLocality: "Cincinnati"
    s:addressRegion: "OH"
    s:postalCode: "45229"
    s:streetAddress: "3333 Burnet Ave"
    s:telephone: "+1(513)636-4200"
  s:logo: "https://www.cincinnatichildrens.org/-/media/cincinnati%20childrens/global%20shared/childrens-logo-new.png"
  s:department:
  - class: s:Organization
    s:legalName: "Allergy and Immunology"
    s:department:
    - class: s:Organization
      s:legalName: "Barski Research Lab"
      s:member:
      - class: s:Person
        s:name: Michael Kotliar
        s:email: mailto:misha.kotliar@gmail.com
        s:sameAs:
        - id: http://orcid.org/0000-0002-6486-3898


doc: |
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
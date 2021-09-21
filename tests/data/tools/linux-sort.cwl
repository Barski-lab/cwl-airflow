cwlVersion: v1.0
class: CommandLineTool


requirements:
  - class: InlineJavascriptRequirement
    expressionLib:
    - var get_output_filename = function() {
          if (inputs.output_filename) {
            return inputs.output_filename;
          }
          return inputs.unsorted_file.location.split('/').slice(-1)[0];
      };


hints:
- class: DockerRequirement
  dockerPull: biowardrobe2/scidap:v0.0.2


inputs:

  unsorted_file:
    type: File
    inputBinding:
      position: 4

  key:
    type:
      type: array
      items: string
      inputBinding:
        prefix: "-k"
    inputBinding:
      position: 1
    doc: |
      -k, --key=POS1[,POS2]
      start a key at POS1, end it at POS2 (origin 1)

  output_filename:
    type: string?
    doc: |
      Name for generated output file


outputs:

  sorted_file:
    type: stdout


stdout: $(get_output_filename())


baseCommand: ["sort"]


$namespaces:
  s: http://schema.org/

$schemas:
- https://github.com/schemaorg/schemaorg/raw/main/data/releases/11.01/schemaorg-current-http.rdf

s:name: "linux-sort"
s:downloadUrl: https://raw.githubusercontent.com/Barski-lab/workflows/master/tools/linux-sort.cwl
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
        s:name: Andrey Kartashov
        s:email: mailto:Andrey.Kartashov@cchmc.org
        s:sameAs:
        - id: http://orcid.org/0000-0001-9102-5681
      - class: s:Person
        s:name: Michael Kotliar
        s:email: mailto:misha.kotliar@gmail.com
        s:sameAs:
        - id: http://orcid.org/0000-0002-6486-3898


doc: |
  Tool sorts data from `unsorted_file` by key
  `default_output_filename` function returns file name identical to `unsorted_file`, if `output_filename` is not provided.
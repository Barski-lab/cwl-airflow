cwlVersion: v1.0
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
    run:
      cwlVersion: v1.0
      class: CommandLineTool


      requirements:
      - class: InlineJavascriptRequirement
        expressionLib:
        - var default_output_filename = function() {
                var ext = (inputs.depth == "-bg" || inputs.depth == "-bga")?".bedGraph":".tab";
                return inputs.input_file.location.split('/').slice(-1)[0].split('.').slice(0,-1).join('.') + ext;
              };


      hints:
      - class: DockerRequirement
        dockerPull: biowardrobe2/bedtools2:v2.26.0


      inputs:

        input_file:
          type: File
          inputBinding:
            position: 16
            valueFrom: |
                ${
                  var prefix = ((/.*\.bam$/i).test(inputs.input_file.path))?'-ibam':'-i';
                  return [prefix, inputs.input_file.path];
                }
          doc: |
            The input file can be in BAM format (Note: BAM must be sorted by position) or <bed/gff/vcf>.
            Prefix is selected on the base of input file extension

        chrom_length_file:
          type: File?
          inputBinding:
            position: 17
            prefix: "-g"
          doc: |
            Input genome file. Needed only when -i flag. The genome file is tab delimited <chromName><TAB><chromSize>

        depth:
          type:
          - "null"
          - type: enum
            name: "depth"
            symbols: ["-bg","-bga","-d", "-dz"]
          inputBinding:
            position: 5
          doc: |
            Report the depth type. By default, bedtools genomecov will compute a histogram of coverage
            for the genome file provided (intputs.chrom_length_file)

        scale:
          type: float?
          inputBinding:
            position: 6
            prefix: -scale
          doc: |
            Scale the coverage by a constant factor.
            Each coverage value is multiplied by this factor before being reported.
            Useful for normalizing coverage by, e.g., reads per million (RPM).
            - Default is 1.0; i.e., unscaled.
            - (FLOAT)

        mapped_reads_number:
          type: int?
          inputBinding:
            position: 7
            prefix: -scale
            valueFrom: |
              ${
                if (inputs.scale){
                  return null;
                } else if (inputs.mapped_reads_number) {
                  return 1000000/inputs.mapped_reads_number;
                } else {
                  return null;
                }
              }
          doc: |
            Optional parameter to calculate scale as 1000000/mapped_reads_number if inputs.scale is not provided

        split:
          type: boolean?
          inputBinding:
            position: 8
            prefix: "-split"
          doc: |
            treat "split" BAM or BED12 entries as distinct BED intervals.
            when computing coverage.
            For BAM files, this uses the CIGAR "N" and "D" operations
            to infer the blocks for computing coverage.
            For BED12 files, this uses the BlockCount, BlockStarts, and BlockEnds
            fields (i.e., columns 10,11,12).

        strand:
          type: string?
          inputBinding:
            position: 9
            prefix: "-strand"
          doc: |
            Calculate coverage of intervals from a specific strand.
            With BED files, requires at least 6 columns (strand is column 6).
            - (STRING): can be + or -

        pairchip:
          type: boolean?
          inputBinding:
            position: 10
            prefix: "-pc"
          doc: |
            pair-end chip seq experiment

        du:
          type: boolean?
          inputBinding:
            position: 11
            prefix: "-du"
          doc: |
            Change strand af the mate read (so both reads from the same strand) useful for strand specific.
            Works for BAM files only

        fragment_size:
          type: int?
          inputBinding:
            position: 12
            prefix: "-fs"
          doc: |
            Set fixed fragment size

        max:
          type: int?
          inputBinding:
            position: 13
            prefix: "-max"
          doc: |
            Combine all positions with a depth >= max into
            a single bin in the histogram. Irrelevant
            for -d and -bedGraph
            - (INTEGER)

        m5:
          type: boolean?
          inputBinding:
            position: 14
            prefix: "-5"
          doc: |
            Calculate coverage of 5" positions (instead of entire interval)

        m3:
          type: boolean?
          inputBinding:
            position: 15
            prefix: "-3"
          doc: |
            Calculate coverage of 3" positions (instead of entire interval)

        output_filename:
          type: string?
          doc: |
            Name for generated output file


      outputs:

        genome_coverage_file:
          type: stdout
          doc: |
            Generated genome coverage output file


      stdout: |
        ${
            return inputs.output_filename ? inputs.output_filename : default_output_filename();
        }


      baseCommand: ["bedtools", "genomecov"]


      $namespaces:
        s: http://schema.org/

      $schemas:
      - https://github.com/schemaorg/schemaorg/raw/main/data/releases/11.01/schemaorg-current-http.rdf

      s:name: "bedtools-genomecov"
      s:downloadUrl: https://raw.githubusercontent.com/Barski-lab/workflows/master/tools/bedtools-genomecov.cwl
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
        Tool calculates genome coverage from input bam/bed/gff/vcf using `bedtools genomecov`

        Depending on `input_file` extension additional prefix is used: if `*.bam` use `-ibam`, else use `-i`.

        `scale` and `mapped_reads_number` inputs result in the same parameter `-scale`. If `scale` is not provided, check if
        `mapped_reads_number` is not null and calculate `-scale` as `1000000/mapped_reads_number`. If both inputs are
        null, `bedtools genomecov` will use its default scaling value.

        `default_output_filename` function returns default output filename and is used when `output_filename` is not provided.
        Default output file extention is `.tab`. If bedGraph should be generated (check flags `inputs.depth`), extension is
        updated to `.bedGraph`. Default basename of the output file is generated on the base of `input_file` basename.


      s:about: |
        Usage: bedtools genomecov [OPTIONS] -i <bed/gff/vcf> -g <genome>

        Options:
          -ibam		The input file is in BAM format.
              Note: BAM _must_ be sorted by position

          -d		Report the depth at each genome position (with one-based coordinates).
              Default behavior is to report a histogram.

          -dz		Report the depth at each genome position (with zero-based coordinates).
              Reports only non-zero positions.
              Default behavior is to report a histogram.

          -bg		Report depth in BedGraph format. For details, see:
              genome.ucsc.edu/goldenPath/help/bedgraph.html

          -bga		Report depth in BedGraph format, as above (-bg).
              However with this option, regions with zero
              coverage are also reported. This allows one to
              quickly extract all regions of a genome with 0
              coverage by applying: "grep -w 0$" to the output.

          -split		Treat "split" BAM or BED12 entries as distinct BED intervals.
              when computing coverage.
              For BAM files, this uses the CIGAR "N" and "D" operations
              to infer the blocks for computing coverage.
              For BED12 files, this uses the BlockCount, BlockStarts, and BlockEnds
              fields (i.e., columns 10,11,12).

          -strand		Calculate coverage of intervals from a specific strand.
              With BED files, requires at least 6 columns (strand is column 6).
              - (STRING): can be + or -

          -pc		Calculate coverage of pair-end fragments.
              Works for BAM files only
          -fs		Force to use provided fragment size instead of read length
              Works for BAM files only
          -du		Change strand af the mate read (so both reads from the same strand) useful for strand specific
              Works for BAM files only
          -5		Calculate coverage of 5" positions (instead of entire interval).

          -3		Calculate coverage of 3" positions (instead of entire interval).

          -max		Combine all positions with a depth >= max into
              a single bin in the histogram. Irrelevant
              for -d and -bedGraph
              - (INTEGER)

          -scale		Scale the coverage by a constant factor.
              Each coverage value is multiplied by this factor before being reported.
              Useful for normalizing coverage by, e.g., reads per million (RPM).
              - Default is 1.0; i.e., unscaled.
              - (FLOAT)

          -trackline	Adds a UCSC/Genome-Browser track line definition in the first line of the output.
              - See here for more details about track line definition:
                    http://genome.ucsc.edu/goldenPath/help/bedgraph.html
              - NOTE: When adding a trackline definition, the output BedGraph can be easily
                    uploaded to the Genome Browser as a custom track,
                    BUT CAN NOT be converted into a BigWig file (w/o removing the first line).

          -trackopts	Writes additional track line definition parameters in the first line.
              - Example:
                -trackopts 'name="My Track" visibility=2 color=255,30,30'
                Note the use of single-quotes if you have spaces in your parameters.
              - (TEXT)

        Notes:
          (1) The genome file should tab delimited and structured as follows:
          <chromName><TAB><chromSize>

          For example, Human (hg19):
          chr1	249250621
          chr2	243199373
          ...
          chr18_gl000207_random	4262

          (2) The input BED (-i) file must be grouped by chromosome.
          A simple "sort -k 1,1 <BED> > <BED>.sorted" will suffice.

          (3) The input BAM (-ibam) file must be sorted by position.
          A "samtools sort <BAM>" should suffice.

        Tips:
          One can use the UCSC Genome Browser's MySQL database to extract
          chromosome sizes. For example, H. sapiens:

          mysql --user=genome --host=genome-mysql.cse.ucsc.edu -A -e \
          "select chrom, size from hg19.chromInfo" > hg19.genome

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
    run:
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
    in:
      unsorted_file: bam_to_bedgraph/genome_coverage_file
      key:
        default: ["1,1","2,2n"]
    out: [sorted_file]

  sorted_bedgraph_to_bigwig:
    run:
      cwlVersion: v1.0
      class: CommandLineTool


      requirements:
      - class: InlineJavascriptRequirement
        expressionLib:
        - var default_output_filename = function() {
                var basename = inputs.bedgraph_file.location.split('/').slice(-1)[0];
                var root = basename.split('.').slice(0,-1).join('.');
                var ext = ".bigWig";
                return (root == "")?basename+ext:root+ext;
              };


      hints:
      - class: DockerRequirement
        dockerPull: biowardrobe2/ucscuserapps:v358


      inputs:

        bedgraph_file:
          type: File
          inputBinding:
            position: 10
          doc: |
            Four column bedGraph file: <chrom> <start> <end> <value>

        chrom_length_file:
          type: File
          inputBinding:
            position: 11
          doc: |
            Two-column chromosome length file: <chromosome name> <size in bases>

        unc:
          type: boolean?
          inputBinding:
            position: 5
            prefix: "-unc"
          doc: |
            Disable compression

        items_per_slot:
          type: int?
          inputBinding:
            separate: false
            position: 6
            prefix: "-itemsPerSlot="
          doc: |
            Number of data points bundled at lowest level. Default 1024

        block_size:
          type: int?
          inputBinding:
            separate: false
            position: 7
            prefix: "-blockSize="
          doc: |
            Number of items to bundle in r-tree.  Default 256

        output_filename:
          type: string?
          inputBinding:
            position: 12
            valueFrom: |
              ${
                  if (self == ""){
                    return default_output_filename();
                  } else {
                    return self;
                  }
              }
          default: ""
          doc: |
            If set, writes the output bigWig file to output_filename,
            otherwise generates filename from default_output_filename()


      outputs:

        bigwig_file:
          type: File
          outputBinding:
            glob: |
              ${
                  if (inputs.output_filename == ""){
                    return default_output_filename();
                  } else {
                    return inputs.output_filename;
                  }
              }


      baseCommand: ["bedGraphToBigWig"]


      $namespaces:
        s: http://schema.org/

      $schemas:
      - https://github.com/schemaorg/schemaorg/raw/main/data/releases/11.01/schemaorg-current-http.rdf

      s:name: "ucsc-bedgraphtobigwig"
      s:downloadUrl: https://raw.githubusercontent.com/Barski-lab/workflows/master/tools/ucsc-bedgraphtobigwig.cwl
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
        Tool converts bedGraph to bigWig file.
        `default_output_filename` function returns filename for generated bigWig if `output_filename` is not provided.
        Default filename is generated on the base of `bedgraph_file` basename with the updated to `*.bigWig` extension.


      s:about: |
        usage:
          bedGraphToBigWig in.bedGraph chrom.sizes out.bw
        where in.bedGraph is a four column file in the format:
              <chrom> <start> <end> <value>
        and chrom.sizes is a two-column file/URL: <chromosome name> <size in bases>
        and out.bw is the output indexed big wig file.
        If the assembly <db> is hosted by UCSC, chrom.sizes can be a URL like
          http://hgdownload.cse.ucsc.edu/goldenPath/<db>/bigZips/<db>.chrom.sizes
        or you may use the script fetchChromSizes to download the chrom.sizes file.
        If not hosted by UCSC, a chrom.sizes file can be generated by running
        twoBitInfo on the assembly .2bit file.
        The input bedGraph file must be sorted, use the unix sort command:
          sort -k1,1 -k2,2n unsorted.bedGraph > sorted.bedGraph
        options:
          -blockSize=N - Number of items to bundle in r-tree.  Default 256
          -itemsPerSlot=N - Number of data points bundled at lowest level. Default 1024
          -unc - If set, do not use compression.

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
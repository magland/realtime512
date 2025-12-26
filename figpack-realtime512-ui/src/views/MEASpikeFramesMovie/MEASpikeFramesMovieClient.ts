import { ZarrDataset, ZarrGroup } from "../../figpack-interface";

export class MEASpikeFramesMovieClient {
  #zarrGroup: ZarrGroup;
  #numSpikes: number;
  #numChannels: number;
  #samplingFrequencyHz: number;
  #dataMin: number;
  #dataMax: number;
  #dataMedian: number;
  #spikeFramesDataDataset: ZarrDataset;
  #electrodeCoords: Float32Array | null = null;
  #spikeTimesSec: Float32Array | null = null;
  #spikeLabels: Int32Array | null = null;

  constructor(
    zarrGroup: ZarrGroup,
    numSpikes: number,
    numChannels: number,
    samplingFrequencyHz: number,
    dataMin: number,
    dataMax: number,
    dataMedian: number,
    spikeFramesDataDataset: ZarrDataset,
  ) {
    this.#zarrGroup = zarrGroup;
    this.#numSpikes = numSpikes;
    this.#numChannels = numChannels;
    this.#samplingFrequencyHz = samplingFrequencyHz;
    this.#dataMin = dataMin;
    this.#dataMax = dataMax;
    this.#dataMedian = dataMedian;
    this.#spikeFramesDataDataset = spikeFramesDataDataset;
  }

  static async create(zarrGroup: ZarrGroup): Promise<MEASpikeFramesMovieClient> {
    const attrs = zarrGroup.attrs;

    const numSpikes = attrs["num_spikes"] as number;
    const numChannels = attrs["num_channels"] as number;
    const samplingFrequencyHz = attrs["sampling_frequency_hz"] as number;
    const dataMin = attrs["data_min"] as number;
    const dataMax = attrs["data_max"] as number;
    const dataMedian = attrs["data_median"] as number;

    // Get the spike frames data dataset
    const spikeFramesDataDataset = await zarrGroup.getDataset("spike_frames_data");
    if (!spikeFramesDataDataset) {
      throw new Error("No spike_frames_data dataset found");
    }

    if (
      numSpikes === undefined ||
      numChannels === undefined ||
      samplingFrequencyHz === undefined ||
      dataMin === undefined ||
      dataMax === undefined ||
      dataMedian === undefined
    ) {
      throw new Error("Missing required attributes in zarr group");
    }

    const client = new MEASpikeFramesMovieClient(
      zarrGroup,
      numSpikes,
      numChannels,
      samplingFrequencyHz,
      dataMin,
      dataMax,
      dataMedian,
      spikeFramesDataDataset,
    );

    // Load spike times and labels
    await client.#loadSpikeTimesAndLabels();

    return client;
  }

  get numSpikes(): number {
    return this.#numSpikes;
  }

  get numChannels(): number {
    return this.#numChannels;
  }

  get samplingFrequencyHz(): number {
    return this.#samplingFrequencyHz;
  }

  get dataMin(): number {
    return this.#dataMin;
  }

  get dataMax(): number {
    return this.#dataMax;
  }

  get dataMedian(): number {
    return this.#dataMedian;
  }

  async getElectrodeCoords(): Promise<Float32Array> {
    if (this.#electrodeCoords === null) {
      const coordsDataset =
        await this.#zarrGroup.getDataset("electrode_coords");
      if (!coordsDataset) {
        throw new Error("No electrode_coords dataset found");
      }
      const data = await coordsDataset.getData({});
      this.#electrodeCoords = data as Float32Array;
    }
    return this.#electrodeCoords;
  }

  async getSpikeFrameData(spikeIndex: number): Promise<Int16Array> {
    if (spikeIndex < 0 || spikeIndex >= this.#numSpikes) {
      throw new Error(
        `Spike index ${spikeIndex} out of range [0, ${this.#numSpikes})`,
      );
    }

    // Load a single spike frame: shape (1, num_channels)
    const data = await this.#spikeFramesDataDataset.getData({
      slice: [
        [spikeIndex, spikeIndex + 1],
        [0, this.#numChannels],
      ],
    });

    return data as Int16Array;
  }

  async #loadSpikeTimesAndLabels(): Promise<void> {
    // Load spike times
    const spikeTimesDataset = await this.#zarrGroup.getDataset("spike_times_sec");
    if (!spikeTimesDataset) {
      throw new Error("No spike_times_sec dataset found");
    }
    const timesData = await spikeTimesDataset.getData({});
    this.#spikeTimesSec = timesData as Float32Array;

    // Load spike labels
    const spikeLabelsDataset = await this.#zarrGroup.getDataset("spike_labels");
    if (!spikeLabelsDataset) {
      throw new Error("No spike_labels dataset found");
    }
    const labelsData = await spikeLabelsDataset.getData({});
    this.#spikeLabels = labelsData as Int32Array;
  }

  getSpikeTime(spikeIndex: number): number {
    if (!this.#spikeTimesSec || spikeIndex < 0 || spikeIndex >= this.#numSpikes) {
      throw new Error(`Invalid spike index: ${spikeIndex}`);
    }
    return this.#spikeTimesSec[spikeIndex];
  }

  getSpikeLabel(spikeIndex: number): number {
    if (!this.#spikeLabels || spikeIndex < 0 || spikeIndex >= this.#numSpikes) {
      throw new Error(`Invalid spike index: ${spikeIndex}`);
    }
    return this.#spikeLabels[spikeIndex];
  }
}

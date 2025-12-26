import React, { useEffect, useState, useCallback, useMemo, useContext } from "react";
import { ZarrGroup } from "../../figpack-interface";
import { MEASpikeFramesMovieClient } from "./MEASpikeFramesMovieClient";
import MEASpikeFramesMovieCanvas from "./MEASpikeFramesMovieCanvas";
import UnitSelectionContext from "../TemplatesView/context-unit-selection/UnitSelectionContext";

type Props = {
  zarrGroup: ZarrGroup;
  width: number;
  height: number;
};

const DEFAULT_CONTRAST = 50;
const DEFAULT_COLORMAP = "grayscale";

const MEASpikeFramesMovieView: React.FC<Props> = ({ zarrGroup, width, height }) => {
  const [client, setClient] = useState<MEASpikeFramesMovieClient | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentSpikeIndex, setCurrentSpikeIndex] = useState<number>(0);
  const [contrast, setContrast] = useState<number>(DEFAULT_CONTRAST);
  const [colormap, setColormap] = useState<string>(DEFAULT_COLORMAP);
  const [electrodeCoords, setElectrodeCoords] = useState<Float32Array | null>(null);
  const [frameData, setFrameData] = useState<Int16Array | null>(null);
  const [filterBySelectedUnits, setFilterBySelectedUnits] = useState<boolean>(false);

  // Get unit selection context
  const unitSelectionContext = useContext(UnitSelectionContext);
  const selectedUnitIds = useMemo(() => {
    return unitSelectionContext?.unitSelection?.selectedUnitIds || new Set<string | number>()
  }, [unitSelectionContext]);

  // Constants for layout
  const controlHeight = 140;
  const canvasHeight = height - controlHeight;

  // Load the client
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const spikeFramesClient = await MEASpikeFramesMovieClient.create(zarrGroup);
        setClient(spikeFramesClient);

        // Load electrode coordinates
        const coords = await spikeFramesClient.getElectrodeCoords();
        setElectrodeCoords(coords);

        // Set initial spike index to 0
        if (spikeFramesClient.numSpikes > 0) {
          setCurrentSpikeIndex(0);
        }
      } catch (err) {
        console.error("Error loading MEA Spike Frames Movie client:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [zarrGroup]);

  const handleSpikeIndexChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const index = parseInt(event.target.value, 10);
      setCurrentSpikeIndex(index);
    },
    [],
  );

  const handleContrastChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setContrast(parseInt(event.target.value, 10));
    },
    [],
  );

  const handleColormapChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      setColormap(event.target.value);
    },
    [],
  );

  const handlePrevSpike = useCallback(() => {
    setCurrentSpikeIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNextSpike = useCallback(() => {
    if (!client) return;
    setCurrentSpikeIndex((prev) => Math.min(client.numSpikes - 1, prev + 1));
  }, [client]);

  const handleFilterBySelectedUnitsChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setFilterBySelectedUnits(event.target.checked);
      // Reset to first spike when toggling filter
      setCurrentSpikeIndex(0);
    },
    [],
  );

  // Filter spike indices based on selected units
  const filteredSpikeIndices = useMemo(() => {
    if (!client || !filterBySelectedUnits || selectedUnitIds.size === 0) {
      // Return all indices
      return Array.from({ length: client?.numSpikes || 0 }, (_, i) => i);
    }

    // Filter by selected units
    const indices: number[] = [];
    for (let i = 0; i < client.numSpikes; i++) {
      const label = client.getSpikeLabel(i);
      if (selectedUnitIds.has(String(label))) {
        indices.push(i);
      }
    }
    return indices;
  }, [client, filterBySelectedUnits, selectedUnitIds]);

  // Map current display index to actual spike index
  const actualSpikeIndex = filteredSpikeIndices[currentSpikeIndex] ?? 0;

  // Load frame data when actual spike index changes
  useEffect(() => {
    if (!client) return;

    const loadFrame = async () => {
      try {
        const data = await client.getSpikeFrameData(actualSpikeIndex);
        setFrameData(data);
      } catch (err) {
        console.error("Error loading spike frame data:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    };
    loadFrame();
  }, [client, actualSpikeIndex]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          width,
          height,
          fontFamily: "Arial, sans-serif",
        }}
      >
        Loading Spike Frames Movie data...
      </div>
    );
  }

  if (error || !client || !electrodeCoords || !frameData) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          width,
          height,
          fontFamily: "Arial, sans-serif",
          color: "red",
        }}
      >
        Error: {error || "Failed to load Spike Frames Movie data"}
      </div>
    );
  }

  const spikeTime = client.getSpikeTime(actualSpikeIndex);
  const spikeLabel = client.getSpikeLabel(actualSpikeIndex);
  const numFilteredSpikes = filteredSpikeIndices.length;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width,
        height,
        fontFamily: "Arial, sans-serif",
        backgroundColor: "#1a1a1a",
      }}
    >
      {/* Canvas for electrode visualization */}
      <div
        style={{
          height: canvasHeight,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: "#000000",
        }}
      >
        <MEASpikeFramesMovieCanvas
          electrodeCoords={electrodeCoords}
          frameData={frameData}
          dataMin={client.dataMin}
          dataMax={client.dataMax}
          dataMedian={client.dataMedian}
          contrast={contrast}
          colormap={colormap}
          width={width}
          height={canvasHeight}
        />
      </div>

      {/* Controls */}
      <div
        style={{
          height: controlHeight,
          padding: "15px",
          backgroundColor: "#2a2a2a",
          borderTop: "1px solid #444",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {/* Navigation and Settings */}
        <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <button
            onClick={handlePrevSpike}
            disabled={currentSpikeIndex === 0}
            style={{
              padding: "8px 16px",
              fontSize: "14px",
              backgroundColor: currentSpikeIndex === 0 ? "#555" : "#4a90e2",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: currentSpikeIndex === 0 ? "not-allowed" : "pointer",
              fontWeight: "bold",
            }}
          >
            ← Prev
          </button>

          <button
            onClick={handleNextSpike}
            disabled={currentSpikeIndex >= numFilteredSpikes - 1}
            style={{
              padding: "8px 16px",
              fontSize: "14px",
              backgroundColor: currentSpikeIndex >= numFilteredSpikes - 1 ? "#555" : "#4a90e2",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: currentSpikeIndex >= numFilteredSpikes - 1 ? "not-allowed" : "pointer",
              fontWeight: "bold",
            }}
          >
            Next →
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "10px" }}>
            <input
              type="checkbox"
              id="filterBySelectedUnits"
              checked={filterBySelectedUnits}
              onChange={handleFilterBySelectedUnitsChange}
              style={{
                cursor: "pointer",
                width: "16px",
                height: "16px",
              }}
            />
            <label
              htmlFor="filterBySelectedUnits"
              style={{
                fontSize: "12px",
                color: "#ccc",
                cursor: "pointer",
                userSelect: "none",
              }}
            >
              Filter by selected units
            </label>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", color: "#ccc", minWidth: "70px" }}>
              Contrast:
            </span>
            <input
              type="range"
              min={0}
              max={100}
              value={contrast}
              onChange={handleContrastChange}
              style={{
                width: "150px",
                height: "6px",
                background: "#4a4a4a",
                outline: "none",
                borderRadius: "3px",
                cursor: "pointer",
              }}
            />
            <span
              style={{
                fontSize: "12px",
                color: "#ccc",
                minWidth: "30px",
                textAlign: "right",
              }}
            >
              {contrast}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", color: "#ccc", minWidth: "70px" }}>
              Colormap:
            </span>
            <select
              value={colormap}
              onChange={handleColormapChange}
              style={{
                padding: "6px",
                fontSize: "12px",
                backgroundColor: "#3a3a3a",
                color: "#fff",
                border: "1px solid #555",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              <option value="grayscale">Grayscale</option>
              <option value="viridis">Viridis</option>
              <option value="hot">Hot</option>
              <option value="blue-red">Blue-Red</option>
              <option value="cool">Cool</option>
            </select>
          </div>
        </div>

        {/* Spike Slider and Info */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "12px", color: "#ccc", minWidth: "50px" }}>
            Spike:
          </span>
          <input
            type="range"
            min={0}
            max={Math.max(0, numFilteredSpikes - 1)}
            value={currentSpikeIndex}
            onChange={handleSpikeIndexChange}
            style={{
              flex: 1,
              height: "6px",
              background: "#4a4a4a",
              outline: "none",
              borderRadius: "3px",
              cursor: "pointer",
            }}
          />
        </div>

        {/* Spike Information Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "20px",
            fontSize: "13px",
            color: "#fff",
            backgroundColor: "#333",
            padding: "8px 12px",
            borderRadius: "4px",
          }}
        >
          <span>
            <strong>Spike:</strong> {currentSpikeIndex + 1} / {numFilteredSpikes}
            {filterBySelectedUnits && selectedUnitIds.size > 0 && (
              <span style={{ color: "#aaa", marginLeft: "5px" }}>
                (of {client.numSpikes} total)
              </span>
            )}
          </span>
          <span>
            <strong>Time:</strong> {spikeTime.toFixed(4)} s
          </span>
          <span>
            <strong>Unit:</strong> {spikeLabel}
          </span>
          <span style={{ marginLeft: "auto", color: "#aaa" }}>
            Channels: {client.numChannels}
          </span>
        </div>
      </div>
    </div>
  );
};

export default MEASpikeFramesMovieView;

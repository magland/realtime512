import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ZarrGroup } from "../../figpack-interface";
import { TemplatesViewClient } from "./TemplatesViewClient";
import TemplateView from "./TemplateView";
import { useSelectedUnitIds, useUnitSelection } from "./context-unit-selection/UnitSelectionContext";

type Props = {
  width: number;
  height: number;
  zarrGroup: ZarrGroup;
};

const TemplatesView: React.FC<Props> = ({ width, height, zarrGroup }) => {
  const [client, setClient] = useState<TemplatesViewClient | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { unitSelectionDispatch} = useUnitSelection();

  // Load the client
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const templatesClient = await TemplatesViewClient.create(zarrGroup);
        unitSelectionDispatch({
          type: "INITIALIZE_UNITS",
          newUnitOrder: Array.from({length: templatesClient.numTemplates}, (_, i) => String(i + 1)),
        })
        setClient(templatesClient);
      } catch (err) {
        console.error("Error loading Templates View client:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [zarrGroup, unitSelectionDispatch]);

  const { selectedUnitIdsArray: selectedUnitIds, allOrderedUnitIds } = useSelectedUnitIds();
  const [onlyShowSelected, setOnlyShowSelected] = useState(false);
  const [useGlobalScale, setUseGlobalScale] = useState(false);
  const [brightness, setBrightness] = useState(50);
  const [globalMin, setGlobalMin] = useState<number | undefined>(undefined);
  const [globalMax, setGlobalMax] = useState<number | undefined>(undefined);

  const selectUnitId = useCallback(
    (unitId: string) => {
      unitSelectionDispatch({
        type: "SET_SELECTION",
        incomingSelectedUnitIds: [unitId]
      });
    },
    [unitSelectionDispatch]
  );

  const toggleSelectUnitId = useCallback(
    (unitId: string) => {
      unitSelectionDispatch({
        type: "TOGGLE_UNIT",
        targetUnit: unitId
      });
    },
    [unitSelectionDispatch],
  );

  const boxMargin = 20;
  const boxWidth = useMemo(() => {
    if (width < 300) {
      return width - boxMargin * 2;
    }
    else if (width < 600) {
      return (width - boxMargin * 3) / 2;
    }
    else if (width < 900) {
      return (width - boxMargin * 4) / 3;
    }
    else {
      return (width - boxMargin * 5) / 4;
    }
  }, [width]);

  const aspectRatio = 1.6;
  const boxHeight = boxWidth / aspectRatio;

  // Determine which units to display
  const displayUnitIds = onlyShowSelected ? selectedUnitIds : allOrderedUnitIds;

  // Create a set for quick lookup of selected units
  const selectedUnitIdsSet = useMemo(
    () => new Set(selectedUnitIds),
    [selectedUnitIds]
  );

  // Compute global min/max when useGlobalScale is enabled
  useEffect(() => {
    if (!useGlobalScale || !client) {
      setGlobalMin(undefined);
      setGlobalMax(undefined);
      return;
    }

    const computeGlobalMinMax = async () => {
      let gMin = Infinity;
      let gMax = -Infinity;

      for (let unitIndex = 0; unitIndex < client.numTemplates; unitIndex++) {
        try {
          const data = await client.templatesDataset.getData({
            slice: [[unitIndex, unitIndex + 1]],
          });

          if (data) {
            const templateData = data as Float32Array;
            for (let i = 0; i < templateData.length; i++) {
              if (templateData[i] < gMin) gMin = templateData[i];
              if (templateData[i] > gMax) gMax = templateData[i];
            }
          }
        } catch (err) {
          console.error(`Error loading template ${unitIndex}:`, err);
        }
      }

      setGlobalMin(gMin);
      setGlobalMax(gMax);
    };

    computeGlobalMinMax();
  }, [useGlobalScale, client]);

  const toolbarHeight = 50;
  const contentHeight = height - toolbarHeight;

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
        Loading Templates View data...
      </div>
    );
  }

  if (error || !client) {
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
        Error: {error || "Failed to load Templates View data"}
      </div>
    );
  }

  if (selectedUnitIds.length === 0 && onlyShowSelected) {
    return (
      <div style={{ width, height, display: "flex", flexDirection: "column" }}>
        <div
          style={{
            width,
            height: contentHeight,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            fontFamily: "Arial, sans-serif",
            color: "#666",
            backgroundColor: "#f8f8f8",
          }}
        >
          No units selected
        </div>
        <Toolbar
          width={width}
          height={toolbarHeight}
          onlyShowSelected={onlyShowSelected}
          onToggle={() => setOnlyShowSelected(!onlyShowSelected)}
          useGlobalScale={useGlobalScale}
          onToggleGlobalScale={() => setUseGlobalScale(!useGlobalScale)}
          brightness={brightness}
          onBrightnessChange={setBrightness}
        />
      </div>
    );
  }

  return (
    <div style={{ width, height, display: "flex", flexDirection: "column" }}>
      <div
        style={{
          width,
          height: contentHeight,
          overflowY: "auto",
          overflowX: "hidden",
          backgroundColor: "#f8f8f8",
          padding: boxMargin,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: `${boxMargin}px`,
            alignContent: "flex-start",
          }}
        >
          {displayUnitIds.map((unitId) => {
            const isSelected = selectedUnitIdsSet.has(unitId);
            return (
              <div
                key={unitId}
                style={{
                  width: boxWidth,
                  height: boxHeight,
                  flexShrink: 0,
                  cursor: "pointer",
                  border: isSelected && !onlyShowSelected ? "3px solid #007bff" : "3px solid transparent",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                }}
                onClick={(e) => {
                  if (e.ctrlKey || e.shiftKey) {
                    toggleSelectUnitId(String(unitId));
                  } else {
                    selectUnitId(String(unitId));
                  }
                }}
              >
                <TemplateView
                  client={client}
                  width={boxWidth - 6}
                  height={boxHeight - 6}
                  unitId={String(unitId)}
                  brightness={brightness}
                  useGlobalScale={useGlobalScale}
                  globalMin={globalMin}
                  globalMax={globalMax}
                />
              </div>
            );
          })}
        </div>
      </div>
      <Toolbar
        width={width}
        height={toolbarHeight}
        onlyShowSelected={onlyShowSelected}
        onToggle={() => setOnlyShowSelected(!onlyShowSelected)}
        useGlobalScale={useGlobalScale}
        onToggleGlobalScale={() => setUseGlobalScale(!useGlobalScale)}
        brightness={brightness}
        onBrightnessChange={setBrightness}
      />
    </div>
  );
};

type ToolbarProps = {
  width: number;
  height: number;
  onlyShowSelected: boolean;
  onToggle: () => void;
  useGlobalScale: boolean;
  onToggleGlobalScale: () => void;
  brightness: number;
  onBrightnessChange: (value: number) => void;
};

const Toolbar: React.FC<ToolbarProps> = ({ 
  width, 
  height, 
  onlyShowSelected, 
  onToggle, 
  useGlobalScale, 
  onToggleGlobalScale,
  brightness,
  onBrightnessChange
}) => {
  return (
    <div
      style={{
        width,
        height,
        backgroundColor: "#fff",
        borderTop: "1px solid #ddd",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        boxSizing: "border-box",
      }}
    >
      <label
        style={{
          display: "flex",
          alignItems: "center",
          cursor: "pointer",
          fontFamily: "Arial, sans-serif",
          fontSize: "14px",
          userSelect: "none",
          marginRight: "20px",
        }}
      >
        <input
          type="checkbox"
          checked={onlyShowSelected}
          onChange={onToggle}
          style={{
            marginRight: "8px",
            cursor: "pointer",
          }}
        />
        Only show selected
      </label>
      <label
        style={{
          display: "flex",
          alignItems: "center",
          cursor: "pointer",
          fontFamily: "Arial, sans-serif",
          fontSize: "14px",
          userSelect: "none",
          marginRight: "20px",
        }}
      >
        <input
          type="checkbox"
          checked={useGlobalScale}
          onChange={onToggleGlobalScale}
          style={{
            marginRight: "8px",
            cursor: "pointer",
          }}
        />
        Global scale
      </label>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          fontFamily: "Arial, sans-serif",
          fontSize: "14px",
        }}
      >
        <label
          style={{
            marginRight: "10px",
            userSelect: "none",
          }}
        >
          Brightness:
        </label>
        <input
          type="range"
          min="0"
          max="100"
          value={brightness}
          onChange={(e) => onBrightnessChange(Number(e.target.value))}
          style={{
            width: "150px",
            marginRight: "10px",
          }}
        />
      </div>
    </div>
  );
};

export default TemplatesView;

import { useState, useEffect } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { dciAPI } from '../api/dci';
import "leaflet/dist/leaflet.css";

const zones = [
  {
    id: 1,
    name: 'Koramangala 5th Block',
    shortName: 'Koramangala',
    lat: 12.9352,
    lng: 77.6245,
    dci: 78,
    workersAffected: 48,
    status: '⚠️ Payout Eligible',
    triggers: ['Rain', 'AQI']
  },
  {
    id: 2,
    name: 'HSR Layout',
    shortName: 'HSR Layout',
    lat: 12.9116,
    lng: 77.6412,
    dci: 42,
    workersAffected: 18,
    status: '✓ Normal',
    triggers: ['Heat']
  },
  {
    id: 3,
    name: 'Whitefield',
    shortName: 'Whitefield',
    lat: 12.9698,
    lng: 77.75,
    dci: 67,
    workersAffected: 35,
    status: '⚠️ Monitoring',
    triggers: ['Rain', 'AQI']
  },
];

export const Heatmap = () => {
  const [selectedZone, setSelectedZone] = useState(zones[0]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [simulationActive, setSimulationActive] = useState(false);
  const [selectedSimulationZone, setSelectedSimulationZone] = useState('Koramangala');
  const [disruptionType, setDisruptionType] = useState('Rain');
  const [intensity, setIntensity] = useState(50);
  const [liveZones, setLiveZones] = useState(zones);
  const [loading, setLoading] = useState(true);

  // Fetch live DCI alerts on mount
  useEffect(() => {
    const fetchLatestAlerts = async () => {
      try {
        setLoading(true);
        const response = await dciAPI.getLatestAlerts();
        // Transform API response to zone format if available, else use mock
        if (response.data && Array.isArray(response.data.alerts)) {
          const mappedZones = response.data.alerts.map((alert, idx) => ({
            id: idx + 1,
            name: alert.area_name || 'Unknown Zone',
            shortName: alert.pincode,
            lat: 12.9 + (idx * 0.05),
            lng: 77.6 + (idx * 0.05),
            dci: Math.round(alert.dci_score || 0),
            workersAffected: Math.round(Math.random() * 50),
            status: alert.dci_score >= 65 ? '⚠️ Payout Eligible' : '✓ Normal',
            triggers: ['DCI Event']
          }));
          setLiveZones(mappedZones.length > 0 ? mappedZones : zones);
        } else {
          setLiveZones(zones);
        }
      } catch (err) {
        console.error('Error fetching DCI alerts:', err);
        setLiveZones(zones);
      } finally {
        setLoading(false);
      }
    };

    fetchLatestAlerts();
  }, []);

  // Initialize map when liveZones change
  useEffect(() => {
    let map;

    const initMap = async () => {
      const L = (await import("leaflet")).default;

      const container = L.DomUtil.get("map-container");
      if (container && container._leaflet_id) {
        container._leaflet_id = null;
      }

      map = L.map("map-container").setView([12.9716, 77.5946], 12);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

      liveZones.forEach((zone) => {
        const circle = L.circleMarker([zone.lat, zone.lng], {
          radius: Math.max(10, zone.dci / 2),
          fillColor: zone.dci > 64 ? "#f59e0b" : "#22c55e",
          color: zone.dci > 64 ? "#d97706" : "#16a34a",
          weight: 2,
          fillOpacity: 0.7,
        }).addTo(map);

        circle.bindPopup(`
          <div>
            <strong>${zone.name}</strong><br/>
            DCI: ${zone.dci}<br/>
            Workers: ${zone.workersAffected}
          </div>
        `);

        circle.on("click", () => setSelectedZone(zone));
      });
    };

    initMap();

    return () => {
      if (map) map.remove();
    };
  }, [liveZones]);

  // ✅ FIXED meaningful breakdown
  const dciBreakdownData = selectedZone.triggers.map((t) => {
    if (t === 'Rain') return { name: 'Rain', value: 40 };
    if (t === 'AQI') return { name: 'AQI', value: 30 };
    if (t === 'Heat') return { name: 'Heat', value: 30 };
    return { name: t, value: 20 };
  });

  const COLORS = ['#FF6B35', '#F59E0B', '#EF4444', '#8B5CF6'];

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Live Heatmap</h1>
        <button
          onClick={async () => {
            setIsRefreshing(true);
            try {
              const response = await dciAPI.getLatestAlerts();
              if (response.data?.alerts) {
                const mappedZones = response.data.alerts.map((alert, idx) => ({
                  id: idx + 1,
                  name: alert.area_name || 'Unknown Zone',
                  shortName: alert.pincode,
                  lat: 12.9 + (idx * 0.05),
                  lng: 77.6 + (idx * 0.05),
                  dci: Math.round(alert.dci_score || 0),
                  workersAffected: Math.round(Math.random() * 50),
                  status: alert.dci_score >= 65 ? '⚠️ Payout Eligible' : '✓ Normal',
                  triggers: ['DCI Event']
                }));
                setLiveZones(mappedZones.length > 0 ? mappedZones : zones);
              }
            } catch (err) {
              console.error('Refresh error:', err);
            } finally {
              setTimeout(() => setIsRefreshing(false), 1000);
            }
          }}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded"
        >
          <RefreshCw className={`${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* MAP */}
        <div className="lg:col-span-3">
          <div id="map-container" className="w-full h-[500px] rounded border" />
        </div>

        {/* SIDE PANEL */}
        <div className="space-y-6">

          {/* ✅ NEW: Zone Status Feed */}
          <div className="p-4 rounded-xl bg-white border shadow-sm">
            <h3 className="mb-3 font-semibold flex gap-2 items-center">
              <AlertCircle size={16}/> Zone Status
            </h3>

            <div className="space-y-2">
              {liveZones.map((z) => {
                const color =
                  z.dci > 84
                    ? "bg-red-100 text-red-700"
                    : z.dci > 64
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-green-100 text-green-700";

                return (
                  <div
                    key={z.id}
                    onClick={() => setSelectedZone(z)}
                    className="p-3 rounded-lg cursor-pointer hover:bg-gray-100 border"
                  >
                    <div className="flex justify-between">
                      <span className="font-medium">{z.shortName}</span>
                      <span className={`text-xs px-2 py-1 rounded ${color}`}>
                        DCI {z.dci}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {z.status}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ✅ FIXED Pie Chart */}
          <div className="p-4 border rounded relative">
            <h3 className="mb-3 font-semibold">
              DCI Breakdown ({selectedZone.shortName})
            </h3>

            <div className="h-40 relative flex items-center justify-center">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={dciBreakdownData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={60}
                    label
                  >
                    {dciBreakdownData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>

              {/* Center DCI */}
              <div className="absolute text-lg font-bold">
                {selectedZone.dci}
              </div>
            </div>
          </div>

          {/* Simulation */}
          <div className="p-4 border rounded space-y-3">
            <h3 className="font-semibold">Simulation</h3>

            <select
              value={selectedSimulationZone}
              onChange={(e) => setSelectedSimulationZone(e.target.value)}
              className="w-full border p-2 rounded"
            >
              {liveZones.map(z => (
                <option key={z.id}>{z.shortName}</option>
              ))}
            </select>

            <select
              value={disruptionType}
              onChange={(e) => setDisruptionType(e.target.value)}
              className="w-full border p-2 rounded"
            >
              <option>Rain</option>
              <option>AQI</option>
              <option>Heat</option>
            </select>

            <input
              type="range"
              value={intensity}
              onChange={(e) => setIntensity(e.target.value)}
              className="w-full"
            />

            <button
              onClick={() => {
                setSimulationActive(true);
                setTimeout(() => setSimulationActive(false), 1500);
              }}
              className="w-full bg-orange-500 text-white p-2 rounded"
            >
              {simulationActive ? "Simulating..." : "Trigger"}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};

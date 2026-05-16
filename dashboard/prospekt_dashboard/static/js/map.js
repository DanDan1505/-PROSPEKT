const map = L.map("map", {
  zoomControl: true,
  scrollWheelZoom: true,
}).setView([5.3, -2.0], 11);

const onlineTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
});

onlineTiles.on("tileerror", () => {
  document.getElementById("map-mode-note").textContent =
    "Offline mode: basemap tiles are unavailable, but zones and dashboard tools are local.";
});

onlineTiles.on("load", () => {
  document.getElementById("map-mode-note").textContent =
    "Online basemap active. Zone data, filters, alerts, and logs are local.";
});

onlineTiles.addTo(map);

const colors = {
  high: "#cf2e2e",
  medium: "#d8a300",
  low: "#2f8f46",
};

let alertThreshold = 70;

function confidenceClass(score) {
  if (score > 70) {
    return "high";
  }

  if (score >= 40) {
    return "medium";
  }

  return "low";
}

function zoneStyle(feature) {
  const confidence = confidenceClass(feature.properties.prospectivity_score);
  const color = colors[confidence] || "#5f6b61";
  const isAlert = feature.properties.prospectivity_score >= alertThreshold;

  return {
    color: isAlert ? "#111711" : color,
    fillColor: color,
    fillOpacity: isAlert ? 0.72 : 0.52,
    opacity: 0.95,
    weight: isAlert ? 3 : 1,
  };
}

function popupHtml(properties) {
  const confidence = confidenceClass(properties.prospectivity_score);

  return `
    <div class="zone-popup">
      <strong>${properties.zone_id}</strong>
      <span>${confidence.toUpperCase()} confidence</span>
      <dl>
        <dt>Prospectivity</dt>
        <dd>${properties.prospectivity_score.toFixed(2)}%</dd>
        <dt>Random Forest</dt>
        <dd>${properties.random_forest_score.toFixed(2)}%</dd>
        <dt>XGBoost</dt>
        <dd>${properties.xgboost_score.toFixed(2)}%</dd>
        <dt>Status</dt>
        <dd>${properties.prediction_status}</dd>
      </dl>
    </div>
  `;
}

function highlightZone(event) {
  event.target.setStyle({
    fillOpacity: 0.78,
    weight: 2,
  });
}

function resetZone(event) {
  zonesLayer.resetStyle(event.target);
}

let zonesLayer;
let allFeatures = [];
const zoneLayersById = {};

function formatCoordinate(value) {
  return Number(value).toFixed(5);
}

function updateZoneDetail(properties) {
  document.getElementById("detail-zone-id").textContent = properties.zone_id;
  document.getElementById("detail-coordinates").textContent =
    `${formatCoordinate(properties.center_latitude)} N, ${formatCoordinate(Math.abs(properties.center_longitude))} W`;
  document.getElementById("detail-confidence").textContent =
    `${properties.prospectivity_score.toFixed(2)}% (${confidenceClass(properties.prospectivity_score)})`;
  document.getElementById("detail-date").textContent = properties.satellite_date_range;
  document.getElementById("detail-status").textContent = properties.prediction_status;

  const drivers = document.getElementById("detail-drivers");
  drivers.innerHTML = "";
  properties.top_drivers.forEach((driver) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <span>${driver.name}</span>
      <strong>${driver.value}</strong>
    `;
    drivers.appendChild(item);
  });
}

function selectZone(feature) {
  updateZoneDetail(feature.properties);
  const layer = zoneLayersById[feature.properties.zone_id];
  if (layer) {
    layer.openPopup();
    map.fitBounds(layer.getBounds(), {
      padding: [80, 80],
      maxZoom: 14,
    });
  }
}

function renderZoneLog(features) {
  const body = document.getElementById("zone-log-body");
  body.innerHTML = "";

  features
    .slice()
    .sort((a, b) => b.properties.prospectivity_score - a.properties.prospectivity_score)
    .slice(0, 20)
    .forEach((feature) => {
      const properties = feature.properties;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${properties.zone_id}</td>
        <td>${properties.prospectivity_score.toFixed(2)}%</td>
        <td><span class="class-chip ${confidenceClass(properties.prospectivity_score)}">${confidenceClass(properties.prospectivity_score)}</span></td>
        <td>${formatCoordinate(properties.center_latitude)}</td>
        <td>${formatCoordinate(properties.center_longitude)}</td>
      `;
      row.addEventListener("click", () => selectZone(feature));
      body.appendChild(row);
    });
}

function renderAlertLog(features) {
  const body = document.getElementById("alert-log-body");
  const summary = document.getElementById("alert-summary");
  body.innerHTML = "";

  const alertFeatures = features
    .filter((feature) => feature.properties.prospectivity_score >= alertThreshold)
    .sort((a, b) => b.properties.prospectivity_score - a.properties.prospectivity_score);

  summary.textContent = `${alertFeatures.length} zones are at or above ${alertThreshold}% confidence.`;

  if (alertFeatures.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td colspan="5">No zones currently exceed the alert threshold.</td>
    `;
    body.appendChild(row);
    return;
  }

  alertFeatures.slice(0, 20).forEach((feature) => {
    const properties = feature.properties;
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${properties.zone_id}</td>
      <td>${properties.prospectivity_score.toFixed(2)}%</td>
      <td>${formatCoordinate(properties.center_latitude)}</td>
      <td>${formatCoordinate(properties.center_longitude)}</td>
      <td>${properties.prediction_status}</td>
    `;
    row.addEventListener("click", () => selectZone(feature));
    body.appendChild(row);
  });
}

function percentileThreshold(features, featureName, percentile) {
  const values = features
    .map((feature) => feature.properties[featureName])
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => a - b);

  if (values.length === 0) {
    return 0;
  }

  const index = Math.floor((values.length - 1) * percentile);
  return values[index];
}

function parseQuery(query) {
  const text = query.toLowerCase().trim();
  const filters = [];
  const labels = [];

  if (text.includes("high confidence") || text.includes("high prospect")) {
    filters.push((feature) => feature.properties.prospectivity_score > 70);
    labels.push("confidence above 70%");
  } else if (text.includes("medium confidence")) {
    filters.push((feature) => {
      const score = feature.properties.prospectivity_score;
      return score >= 40 && score <= 70;
    });
    labels.push("confidence between 40% and 70%");
  } else if (text.includes("low confidence")) {
    filters.push((feature) => feature.properties.prospectivity_score < 40);
    labels.push("confidence below 40%");
  }

  if (text.includes("iron")) {
    const threshold = percentileThreshold(allFeatures, "iron_oxide_index_mean", 0.75);
    filters.push((feature) => feature.properties.iron_oxide_index_mean >= threshold);
    labels.push("high iron oxide");
  }

  if (text.includes("clay")) {
    const threshold = percentileThreshold(allFeatures, "clay_mineral_index_mean", 0.75);
    filters.push((feature) => feature.properties.clay_mineral_index_mean >= threshold);
    labels.push("high clay mineral index");
  }

  if (text.includes("slope") || text.includes("steep")) {
    const threshold = percentileThreshold(allFeatures, "slope_degrees_mean", 0.75);
    filters.push((feature) => feature.properties.slope_degrees_mean >= threshold);
    labels.push("steep slope");
  }

  if (text.includes("vegetation") || text.includes("exposed")) {
    const threshold = percentileThreshold(allFeatures, "ndvi_mean", 0.25);
    filters.push((feature) => feature.properties.ndvi_mean <= threshold);
    labels.push("low vegetation exposure");
  }

  if (text.includes("tarkwa") || text.includes("near")) {
    const tarkwa = { latitude: 5.3, longitude: -2.0 };
    filters.push((feature) => {
      const latitudeDistance = feature.properties.center_latitude - tarkwa.latitude;
      const longitudeDistance = feature.properties.center_longitude - tarkwa.longitude;
      const distance = Math.sqrt(latitudeDistance ** 2 + longitudeDistance ** 2);
      return distance <= 0.12;
    });
    labels.push("near Tarkwa");
  }

  return { filters, labels };
}

function applyQuery(query) {
  const { filters, labels } = parseQuery(query);
  const filteredFeatures = filters.length === 0
    ? allFeatures
    : allFeatures.filter((feature) => filters.every((filter) => filter(feature)));

  renderZones(filteredFeatures);
  renderZoneLog(filteredFeatures);
  renderAlertLog(filteredFeatures);

  const summary = document.getElementById("query-summary");
  if (filters.length === 0) {
    summary.textContent = `Showing all ${allFeatures.length} satellite-predicted zones.`;
  } else {
    summary.textContent = `Showing ${filteredFeatures.length} of ${allFeatures.length} zones matching: ${labels.join(", ")}.`;
  }

  if (filteredFeatures.length > 0) {
    updateZoneDetail(filteredFeatures[0].properties);
  }
}

function renderZones(features) {
  if (zonesLayer) {
    zonesLayer.remove();
  }

  Object.keys(zoneLayersById).forEach((zoneId) => {
    delete zoneLayersById[zoneId];
  });

  zonesLayer = L.geoJSON(
    {
      type: "FeatureCollection",
      features,
    },
    {
      style: zoneStyle,
      onEachFeature: (feature, layer) => {
        zoneLayersById[feature.properties.zone_id] = layer;
        layer.bindPopup(popupHtml(feature.properties));
        layer.on({
          click: () => updateZoneDetail(feature.properties),
          mouseover: highlightZone,
          mouseout: resetZone,
        });
      },
    },
  ).addTo(map);

  if (features.length > 0) {
    map.fitBounds(zonesLayer.getBounds(), {
      padding: [16, 16],
      maxZoom: 14,
    });
  }
}

function applyThreshold(value) {
  const parsedValue = Number(value);
  alertThreshold = Number.isFinite(parsedValue)
    ? Math.max(0, Math.min(100, parsedValue))
    : 70;

  const currentQuery = document.getElementById("query-input").value;
  applyQuery(currentQuery);
}

fetch("/api/zones")
  .then((response) => response.json())
  .then((data) => {
    allFeatures = data.features;
    renderZones(allFeatures);
    renderZoneLog(allFeatures);
    renderAlertLog(allFeatures);
    if (data.features.length > 0) {
      updateZoneDetail(data.features[0].properties);
    }
  })
  .catch((error) => {
    const mapElement = document.getElementById("map");
    mapElement.innerHTML = `<div class="map-error">Map data could not be loaded: ${error}</div>`;
  });

document.getElementById("query-form").addEventListener("submit", (event) => {
  event.preventDefault();
  applyQuery(document.getElementById("query-input").value);
});

document.getElementById("query-reset").addEventListener("click", () => {
  document.getElementById("query-input").value = "";
  applyQuery("");
});

document.getElementById("threshold-input").addEventListener("input", (event) => {
  applyThreshold(event.target.value);
});

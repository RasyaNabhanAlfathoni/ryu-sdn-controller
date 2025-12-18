const express = require("express");
const { MongoClient } = require("mongodb");

const app = express();
const PORT = 3000;

// Mongo UniFi
const MONGO_URL = "mongodb://127.0.0.1:27117";
const DB_NAME = "ace";

// whitelist collection (PENTING!)
const ALLOWED_COLLECTIONS = [
  "user", // List_of_client
  "usergroup", // List_of_client_group
  "version_history",
  "device", // List_of_device
  "site", // List_of_site
  "admin_activity_log", // List_of_admin_log
  "alert", // list_of_alert
  "alert_setting",
  "dashboard",
  "apgroup",
  "event",
  "wlanconf",
  "wlangroup",
  "networkconf",
  "setting",
  "portconf",
  "privilege",
  "map",
  "radiusprofile",
  "systemevent"
];

let db;

// connect mongo sekali
MongoClient.connect(MONGO_URL)
  .then(client => {
    db = client.db(DB_NAME);
    console.log("✅ MongoDB connected");
  })
  .catch(err => {
    console.error("❌ Mongo error", err);
    process.exit(1);
  });

// ===================== API =====================

app.get("/query_range", async (req, res) => {
  try {
    const field = req.query.field;

    if (!field) {
      return res.status(400).json({ error: "field required" });
    }

    if (!ALLOWED_COLLECTIONS.includes(field)) {
      return res.status(403).json({ error: "collection not allowed" });
    }

    const data = await db
      .collection(field)
      .find({})
      .limit(500) // 🔥 jangan unlimited
      .toArray();

    res.json({
      collection: field,
      count: data.length,
      data
    });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ===============================================

app.listen(PORT, () => {
  console.log(`🚀 API running on http://localhost:${PORT}`);
});

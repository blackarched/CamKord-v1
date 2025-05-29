import React, { useEffect, useState } from "react";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const Dashboard = () => {
  const [nightVision, setNightVision] = useState(false);
  const [autoFocus, setAutoFocus] = useState(false);
  const [snapshotUrl, setSnapshotUrl] = useState(null);

  useEffect(() => {
    axios.defaults.baseURL = "http://localhost:8000/api";
  }, []);

  const toggleNightVision = async () => {
    try {
      await axios.post("/camera/night_vision", { enabled: !nightVision });
      setNightVision(!nightVision);
    } catch (error) {
      console.error("Night vision toggle failed", error);
    }
  };

  const toggleAutoFocus = async () => {
    try {
      await axios.post("/camera/auto_focus", { enabled: !autoFocus });
      setAutoFocus(!autoFocus);
    } catch (error) {
      console.error("Auto focus toggle failed", error);
    }
  };

  const takeSnapshot = async () => {
    try {
      const response = await axios.get("/camera/snapshot", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      setSnapshotUrl(url);
    } catch (error) {
      console.error("Snapshot failed", error);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
      <Card className="col-span-1 md:col-span-2">
        <CardContent>
          <h1 className="text-2xl font-bold mb-4">Live Feed</h1>
          <img
            src="http://localhost:8000/video_feed"
            alt="Live Feed"
            className="w-full h-auto rounded-xl border shadow"
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-4">
          <Button onClick={toggleNightVision} className="w-full">
            {nightVision ? "Disable" : "Enable"} Night Vision
          </Button>
          <Button onClick={toggleAutoFocus} className="w-full">
            {autoFocus ? "Disable" : "Enable"} Auto Focus
          </Button>
          <Button onClick={takeSnapshot} className="w-full">
            Take Snapshot
          </Button>
        </CardContent>
      </Card>

      {snapshotUrl && (
        <Card>
          <CardContent>
            <h2 className="text-lg font-semibold">Snapshot Preview</h2>
            <img
              src={snapshotUrl}
              alt="Snapshot"
              className="rounded-xl mt-2 border shadow"
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;

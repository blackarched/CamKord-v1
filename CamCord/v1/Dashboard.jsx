import React, { useEffect, useState } from "react"; import { Card, CardContent } from "@/components/ui/card"; import { Button } from "@/components/ui/button"; import { Switch } from "@/components/ui/switch"; import { Input } from "@/components/ui/input"; import { Video } from "lucide-react"; import axios from "axios";

export default function Dashboard() { const [nightVision, setNightVision] = useState(false); const [autofocus, setAutofocus] = useState(true); const [videoStreamUrl, setVideoStreamUrl] = useState(""); const [snapshotUrl, setSnapshotUrl] = useState("");

useEffect(() => { setVideoStreamUrl("http://localhost:8000/video_feed"); }, []);

const handleNightVisionToggle = async () => { try { const response = await axios.post("/api/toggle_night_vision"); setNightVision(response.data.night_vision); } catch (error) { console.error("Error toggling night vision:", error); } };

const handleAutofocusToggle = async () => { try { const response = await axios.post("/api/toggle_autofocus"); setAutofocus(response.data.autofocus); } catch (error) { console.error("Error toggling autofocus:", error); } };

const takeSnapshot = async () => { try { const response = await axios.get("/api/snapshot"); setSnapshotUrl(response.data.image_url); } catch (error) { console.error("Error taking snapshot:", error); } };

return ( <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6"> <Card className="rounded-2xl shadow-md"> <CardContent className="flex flex-col items-center justify-center p-4"> <h2 className="text-xl font-semibold mb-4">Live Camera Feed</h2> <video src={videoStreamUrl} autoPlay muted controls className="w-full rounded-lg" /> </CardContent> </Card>

<Card className="rounded-2xl shadow-md">
    <CardContent className="p-4 space-y-4">
      <h2 className="text-xl font-semibold">Controls</h2>
      <div className="flex items-center justify-between">
        <span>Night Vision</span>
        <Switch checked={nightVision} onCheckedChange={handleNightVisionToggle} />
      </div>
      <div className="flex items-center justify-between">
        <span>Auto Focus</span>
        <Switch checked={autofocus} onCheckedChange={handleAutofocusToggle} />
      </div>
      <Button onClick={takeSnapshot} className="w-full mt-4">
        Take Snapshot
      </Button>
      {snapshotUrl && (
        <div className="mt-4">
          <img src={snapshotUrl} alt="Snapshot" className="rounded-lg shadow" />
        </div>
      )}
    </CardContent>
  </Card>
</div>

); }

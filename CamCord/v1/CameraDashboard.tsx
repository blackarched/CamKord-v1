import React, { useEffect, useState } from "react"; import { Card, CardContent } from "@/components/ui/card"; import { Button } from "@/components/ui/button"; import { Input } from "@/components/ui/input"; import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"; import { toast } from "sonner";

const Dashboard = () => { const [cameras, setCameras] = useState([]); const [events, setEvents] = useState([]); const [selectedCamera, setSelectedCamera] = useState(null); const [settings, setSettings] = useState({});

useEffect(() => { fetch("/api/cameras") .then(res => res.json()) .then(setCameras) .catch(() => toast.error("Failed to fetch cameras"));

fetch("/api/events")
  .then(res => res.json())
  .then(setEvents)
  .catch(() => toast.error("Failed to fetch events"));

}, []);

const handleSettingsChange = (e) => { const { name, value } = e.target; setSettings(prev => ({ ...prev, [name]: value })); };

const handleSettingsSubmit = (id) => { fetch(/api/settings/${id}, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings), }) .then(res => res.json()) .then(() => toast.success("Settings updated")) .catch(() => toast.error("Failed to update settings")); };

return ( <Tabs defaultValue="live" className="w-full p-4"> <TabsList> <TabsTrigger value="live">Live Feeds</TabsTrigger> <TabsTrigger value="events">Event Logs</TabsTrigger> <TabsTrigger value="settings">Settings</TabsTrigger> </TabsList>

<TabsContent value="live">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cameras.map((cam) => (
        <Card key={cam.id}>
          <CardContent className="p-2">
            <h3 className="font-semibold mb-2">{cam.name}</h3>
            <img
              src={`/api/cameras/${cam.id}/feed`}
              alt={`Camera ${cam.id}`}
              className="w-full rounded"
            />
          </CardContent>
        </Card>
      ))}
    </div>
  </TabsContent>

  <TabsContent value="events">
    <div className="space-y-2">
      {events.map((evt, i) => (
        <Card key={i}>
          <CardContent className="p-2 text-sm">
            <div><strong>Camera:</strong> {evt.camera_id}</div>
            <div><strong>Time:</strong> {new Date(evt.timestamp).toLocaleString()}</div>
            <div><strong>Event:</strong> {evt.event}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  </TabsContent>

  <TabsContent value="settings">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cameras.map((cam) => (
        <Card key={cam.id}>
          <CardContent className="p-4 space-y-2">
            <h3 className="font-semibold">Settings for {cam.name}</h3>
            <Input
              name="night_vision"
              placeholder="Night Vision (on/off)"
              onChange={handleSettingsChange}
            />
            <Input
              name="auto_focus"
              placeholder="Auto Focus (on/off)"
              onChange={handleSettingsChange}
            />
            <Button onClick={() => handleSettingsSubmit(cam.id)}>Update</Button>
          </CardContent>
        </Card>
      ))}
    </div>
  </TabsContent>
</Tabs>

); };

export default Dashboard;

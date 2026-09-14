"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export function PaperPanel() {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur-md">
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">PLOS ONE · 2016</Badge>
          <Badge variant="outline">MIT Senseable City Lab</Badge>
        </div>
        <CardTitle className="font-heading text-lg tracking-tight">
          Revisiting Street Intersections Using Slot-Based Systems
        </CardTitle>
        <CardDescription>
          Tachet, Santi, Sobolevsky, Reyes-Castro, Frazzoli, Helbing, and Ratti. The viral
          “cars zip through a dark intersection” clip is this paper’s companion visualization,
          Light Traffic.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-relaxed text-muted-foreground">
        <p>
          Fully autonomous, communicating cars treat an intersection like an airport runway
          schedule. Each vehicle requests a time slot, then slows or speeds so its front bumper
          arrives at the reserved instant. Nobody waits for a red light. In the video everyone
          remembers, perpendicular streams weave through a grid of space–time tiles and miss
          each other by a few meters.
        </p>
        <p>
          The authors compare three controllers with queuing theory.{" "}
          <span className="text-foreground">FAIR</span> is first-come, first-served.
          <span className="text-foreground"> BATCH</span> platoons same-direction cars when load
          rises — the “slower is faster” trick: some vehicles ease off early so a packed group can
          clear the box without a 5–8 second yellow.{" "}
          <span className="text-foreground">FIXED</span> is a classic two-phase signal. BATCH can
          roughly <span className="text-foreground">double capacity</span> versus signals and
          cuts delay far more than that, because the conflicting-flow “setup” shrinks from
          several seconds to about 1.5s.
        </p>
        <Separator />
        <div className="grid gap-3 sm:grid-cols-2">
          <Fact
            label="What they actually modeled"
            body="A two-road crossing, Poisson arrivals, safety distances, and an analytical capacity/delay comparison — not a 120 mph city grid."
          />
          <Fact
            label="The 45 / 90–120 mph picture"
            body="That speed split is the popular reading of an AV-only city: cruise like a highway on the block, then drop to about 45 mph to thread the slot. The paper’s result is the weave-without-stopping, not those posted limits."
          />
          <Fact
            label="Ancestor work"
            body="Dresner & Stone, 2008: Autonomous Intersection Management. Cars reserve tiles in the box. This sim uses that AIM weave to show what the MIT video made famous."
          />
          <Fact
            label="What it does not solve"
            body="Pedestrians, bikes, human drivers, weather, comms dropouts. One manual car breaks the schedule. The authors also left city-scale networks as future work."
          />
        </div>
        <p className="text-xs">
          Paper:{" "}
          <a
            className="text-primary underline-offset-4 hover:underline"
            href="https://doi.org/10.1371/journal.pone.0149607"
            target="_blank"
            rel="noreferrer"
          >
            doi:10.1371/journal.pone.0149607
          </a>
          {" · "}
          <a
            className="text-primary underline-offset-4 hover:underline"
            href="https://news.mit.edu/2016/no-traffic-lights-communicating-vehicles-intersections-more-efficiently-0317"
            target="_blank"
            rel="noreferrer"
          >
            MIT News
          </a>
          {" · "}
          <a
            className="text-primary underline-offset-4 hover:underline"
            href="https://senseable.mit.edu/wave/"
            target="_blank"
            rel="noreferrer"
          >
            DriveWAVE
          </a>
        </p>
      </CardContent>
    </Card>
  );
}

function Fact({ label, body }: { label: string; body: string }) {
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <div className="mb-1 text-foreground">{label}</div>
      <p>{body}</p>
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import { VISION_COPY, VISION_ICONS } from "@/lib/data";
import { fadeUp, staggerContainer, viewportOnce } from "@/lib/motion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import UrlConverterMachine from "@/components/sections/UrlConverterMachine";

function PersonalMocks() {
  const items = [
    { title: "Code Generation", body: "AI drafts sandbox challenges from transcript segments." },
    { title: "Student Profile", body: "Mastery nodes, streaks, and Tutorial Hell Score." },
    { title: "Mastery Metrics", body: "84% recursion accuracy · 6 concepts solidified." },
    { title: "Checkpoint Stream", body: "Live feed of MCQ, debug, and coding overlays." },
  ];
  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((item) => (
        <Card key={item.title} className="border-ink/10 bg-white">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-sm">{item.title}</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-ink-soft">{item.body}</CardContent>
        </Card>
      ))}
    </div>
  );
}

function EnterpriseMocks() {
  const items = [
    { title: "Cohort Dashboard", body: "Seat utilization, cohort mastery heatmaps, export." },
    { title: "Seat Management", body: "Invite learners, assign curricula, revoke access." },
    { title: "Bulk Ingestion", body: "Queue 50+ YouTube URLs via CSV upload pipeline." },
    { title: "Org Analytics", body: "Department-level Tutorial Hell Score rollups." },
  ];
  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((item) => (
        <Card key={item.title} className="border-ink/10 bg-ink/5">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-sm">{item.title}</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-ink-soft">{item.body}</CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function VisionSplitGrid() {
  return (
    <section id="solutions" className="bg-canvas px-6 py-16 md:py-24">
      <div className="mx-auto grid max-w-container gap-12 md:grid-cols-2">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          variants={staggerContainer}
        >
          <motion.h2 variants={fadeUp} custom={0} className="font-display text-4xl font-bold text-ink">
            {VISION_COPY.heading}
          </motion.h2>
          <motion.p variants={fadeUp} custom={1} className="mt-4 leading-relaxed text-ink-soft">
            {VISION_COPY.body}
          </motion.p>

          <motion.div variants={fadeUp} custom={2} className="relative mt-10 w-full">
            <UrlConverterMachine />
          </motion.div>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          variants={fadeUp}
          id="enterprise"
        >
          <Tabs defaultValue="personal">
            <TabsList className="w-full justify-start rounded-full border border-ink/10 bg-white p-1">
              <TabsTrigger
                value="personal"
                className="data-[state=active]:bg-ink data-[state=active]:text-white"
              >
                Personal
              </TabsTrigger>
              <TabsTrigger
                value="enterprise"
                className="data-[state=active]:bg-ink data-[state=active]:text-white"
              >
                Enterprise
              </TabsTrigger>
            </TabsList>
            <TabsContent value="personal">
              <PersonalMocks />
            </TabsContent>
            <TabsContent value="enterprise">
              <EnterpriseMocks />
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </section>
  );
}

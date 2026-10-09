import * as echarts from "echarts/core";
import { BarChart, GaugeChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, GaugeChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

export { echarts };

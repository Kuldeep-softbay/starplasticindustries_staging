/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlPanelButtons } from "@mrp_workorder/mrp_display/control_panel";

patch(ControlPanelButtons.prototype, {

    onClickShiftHourEntry() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Shift / Hour Entry",
            res_model: "work.center.shift",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    },

});
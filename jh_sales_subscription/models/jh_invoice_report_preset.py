from odoo import api, fields, models


class JhInvoiceReportPreset(models.Model):
    _name = 'jh.invoice.report.preset'
    _description = 'Configuración guardada del reporte de facturas'
    _rec_name = 'jh_name'
    _order = 'jh_name, id'

    jh_name = fields.Char(string='Nombre', required=True, help='Identifica una configuración reutilizable del reporte.\nUse un nombre que describa sus filtros y columnas.')
    jh_user_id = fields.Many2one('res.users', string='Usuario', required=True, default=lambda self: self.env.user, readonly=True, ondelete='cascade', help='Indica el propietario de la configuración privada.\nSolo este usuario puede consultar y modificar la plantilla.')
    jh_company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company, readonly=True, ondelete='cascade', help='Asocia la configuración a la compañía activa al guardarla.\nLa plantilla se ofrece cuando esa compañía está activa.')
    jh_is_default = fields.Boolean(string='Predeterminada', help='Carga esta configuración al abrir el reporte.\nSolo una plantilla puede ser predeterminada por usuario y compañía.')
    jh_settings = fields.Json(string='Configuración', required=True, help='Conserva los filtros, columnas, formato y período del reporte.\nNo almacena archivos generados ni resultados de facturas.')

    _jh_preset_name_unique = models.Constraint(
        'UNIQUE(jh_user_id, jh_company_id, jh_name)',
        'Ya existe una configuración con ese nombre para este usuario y compañía.',
    )

    def _jh_clear_other_defaults(self):
        for preset in self.filtered('jh_is_default'):
            self.search([
                ('jh_user_id', '=', preset.jh_user_id.id),
                ('jh_company_id', '=', preset.jh_company_id.id),
                ('jh_is_default', '=', True),
                ('id', '!=', preset.id),
            ]).write({'jh_is_default': False})

    @api.model_create_multi
    def create(self, vals_list):
        presets = super().create(vals_list)
        # In a batch, the last requested default wins for each user/company.
        for preset, vals in zip(presets, vals_list):
            if vals.get('jh_is_default'):
                preset.write({'jh_is_default': True})
        return presets

    def write(self, vals):
        if vals.get('jh_is_default') and len(self) > 1:
            for preset in self:
                preset.write(vals)
            return True
        result = super().write(vals)
        # Readonly UI fields must not allow transferring a private preset by RPC.
        self.check_access('write')
        if vals.get('jh_is_default'):
            self._jh_clear_other_defaults()
        return result
